/* ==========================================================================
 *  DEER BLINDS & STANDS CO — main.js
 *  Cart (localStorage), drawer, quote modal, mobile menu, category slider,
 *  product sort, checkout summary + freight, and all form submissions.
 *  Vanilla JS only. Loads on every page; everything is null-guarded.
 * ========================================================================== */
(function () {
  "use strict";

  var CFG = window.STORE_CONFIG || {
    freeShipThreshold: 199, flatShipping: 14.99, freight: { "United States (Domestic)": 0 },
    business: {}
  };
  var DOMESTIC = "United States (Domestic)";
  var CART_KEY = "blinds_cart_v1";

  // -------------------------------------------------------------- helpers
  function $(sel, ctx) { return (ctx || document).querySelector(sel); }
  function $all(sel, ctx) { return Array.prototype.slice.call((ctx || document).querySelectorAll(sel)); }
  function money(n) {
    n = Number(n) || 0;
    var dp = (Math.round(n * 100) % 100 === 0) ? 0 : 2;
    return "$" + n.toLocaleString("en-US", { minimumFractionDigits: dp, maximumFractionDigits: 2 });
  }
  function imgUrl(name) {
    if (!name) return "/static/images/placeholder.jpg";
    if (/^https?:\/\//.test(name)) return name;
    return "/static/images/" + name;
  }

  // ============================================================ CART STATE
  var Cart = {
    items: [],
    load: function () {
      try { this.items = JSON.parse(localStorage.getItem(CART_KEY)) || []; }
      catch (e) { this.items = []; }
      if (!Array.isArray(this.items)) this.items = [];
    },
    save: function () {
      try { localStorage.setItem(CART_KEY, JSON.stringify(this.items)); } catch (e) {}
    },
    add: function (item) {
      var found = null;
      for (var i = 0; i < this.items.length; i++) {
        if (this.items[i].slug === item.slug && this.items[i].name === item.name) { found = this.items[i]; break; }
      }
      if (found) { found.qty += (item.qty || 1); }
      else {
        this.items.push({
          slug: item.slug || "", name: item.name || "Item",
          price: Number(item.price) || 0, image: item.image || "placeholder.jpg",
          qty: item.qty || 1
        });
      }
      this.save();
    },
    setQty: function (idx, qty) {
      if (!this.items[idx]) return;
      this.items[idx].qty = qty;
      if (this.items[idx].qty <= 0) this.items.splice(idx, 1);
      this.save();
    },
    remove: function (idx) { this.items.splice(idx, 1); this.save(); },
    count: function () { return this.items.reduce(function (s, it) { return s + it.qty; }, 0); },
    subtotal: function () { return this.items.reduce(function (s, it) { return s + it.price * it.qty; }, 0); }
  };

  // ----------------------------------------------------------- cart badge
  function updateCount() {
    var n = Cart.count();
    $all("[data-cart-count]").forEach(function (el) { el.textContent = n; });
  }

  // --------------------------------------------------------- render drawer
  function renderDrawer() {
    var wrap = $("#cart-items");
    if (!wrap) return;
    if (!Cart.items.length) {
      wrap.innerHTML = '<div class="cart-empty">Your quote cart is empty.<br>Browse blinds &amp; gear to add items.</div>';
    } else {
      wrap.innerHTML = Cart.items.map(function (it, i) {
        return '' +
          '<div class="cart-item">' +
            '<img src="' + imgUrl(it.image) + '" alt="" onerror="this.onerror=null;this.src=\'/static/images/placeholder.jpg\';">' +
            '<div class="cart-item-main">' +
              '<span class="cart-item-name">' + escapeHtml(it.name) + '</span>' +
              '<span class="cart-item-price">' + money(it.price) + '</span>' +
              '<div class="cart-qty">' +
                '<button type="button" data-dec="' + i + '" aria-label="Decrease quantity">&minus;</button>' +
                '<span>' + it.qty + '</span>' +
                '<button type="button" data-inc="' + i + '" aria-label="Increase quantity">+</button>' +
              '</div>' +
              '<button type="button" class="cart-remove" data-remove="' + i + '">Remove</button>' +
            '</div>' +
          '</div>';
      }).join("");
    }
    // subtotal + ship note
    var sub = Cart.subtotal();
    var subEl = $("#cart-subtotal");
    if (subEl) subEl.textContent = money(sub);
    var note = $("#ship-note");
    if (note) {
      if (sub > 0 && sub >= CFG.freeShipThreshold) {
        note.className = "ship-note free";
        note.textContent = "You've unlocked free shipping on accessories.";
      } else if (sub > 0) {
        note.className = "ship-note";
        note.textContent = "Add " + money(CFG.freeShipThreshold - sub) + " more for free accessory shipping.";
      } else {
        note.className = "ship-note";
        note.textContent = "Blinds & towers ship by freight — quoted to your address.";
      }
    }
    updateCount();
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  // drawer wiring (event delegation for qty/remove)
  function wireDrawer() {
    var body = $("#cart-items");
    if (body) {
      body.addEventListener("click", function (e) {
        var t = e.target.closest("button");
        if (!t) return;
        if (t.hasAttribute("data-inc")) { var i = +t.getAttribute("data-inc"); Cart.setQty(i, Cart.items[i].qty + 1); renderDrawer(); }
        else if (t.hasAttribute("data-dec")) { var d = +t.getAttribute("data-dec"); Cart.setQty(d, Cart.items[d].qty - 1); renderDrawer(); }
        else if (t.hasAttribute("data-remove")) { Cart.remove(+t.getAttribute("data-remove")); renderDrawer(); syncCheckout(); }
        syncCheckout();
      });
    }
  }

  // ============================================================== OVERLAYS
  function openPanel(panel, overlay) {
    if (panel) { panel.classList.add("open"); panel.setAttribute("aria-hidden", "false"); }
    if (overlay) overlay.classList.add("open");
    document.body.style.overflow = "hidden";
  }
  function closePanel(panel, overlay) {
    if (panel) { panel.classList.remove("open"); panel.setAttribute("aria-hidden", "true"); }
    if (overlay) overlay.classList.remove("open");
    document.body.style.overflow = "";
  }
  function closeAll() {
    closePanel($("#cart-drawer"), $("#cart-overlay"));
    closePanel($("#quote-modal"), $("#quote-overlay"));
    closePanel($("#mobile-menu-panel"), $("#m-overlay"));
    var hb = $("#hamburger");
    if (hb) { hb.classList.remove("active"); hb.setAttribute("aria-expanded", "false"); }
    document.body.style.overflow = "";
  }

  function wireOverlays() {
    // cart
    $all("[data-cart-open]").forEach(function (b) {
      b.addEventListener("click", function (e) { e.preventDefault(); closeAll(); renderDrawer(); openPanel($("#cart-drawer"), $("#cart-overlay")); });
    });
    var cc = $("#cart-close"); if (cc) cc.addEventListener("click", function () { closePanel($("#cart-drawer"), $("#cart-overlay")); });
    var ck = $("#cart-continue"); if (ck) ck.addEventListener("click", function () { closePanel($("#cart-drawer"), $("#cart-overlay")); });
    var co = $("#cart-overlay"); if (co) co.addEventListener("click", function () { closePanel($("#cart-drawer"), $("#cart-overlay")); });

    // quote modal
    $all("[data-quote-open]").forEach(function (b) {
      b.addEventListener("click", function (e) {
        e.preventDefault();
        closeAll();
        var prod = b.getAttribute("data-product");
        var pf = $("#quote-product");
        if (pf && prod) pf.value = prod;
        openPanel($("#quote-modal"), $("#quote-overlay"));
      });
    });
    var qc = $("#quote-close"); if (qc) qc.addEventListener("click", function () { closePanel($("#quote-modal"), $("#quote-overlay")); });
    var qo = $("#quote-overlay"); if (qo) qo.addEventListener("click", function () { closePanel($("#quote-modal"), $("#quote-overlay")); });

    // mobile menu
    var hb = $("#hamburger");
    if (hb) hb.addEventListener("click", function () {
      var isOpen = $("#mobile-menu-panel") && $("#mobile-menu-panel").classList.contains("open");
      if (isOpen) { closePanel($("#mobile-menu-panel"), $("#m-overlay")); hb.classList.remove("active"); hb.setAttribute("aria-expanded", "false"); }
      else { closeAll(); openPanel($("#mobile-menu-panel"), $("#m-overlay")); hb.classList.add("active"); hb.setAttribute("aria-expanded", "true"); }
    });
    var mmc = $("#mm-close"); if (mmc) mmc.addEventListener("click", closeAll);
    var mo = $("#m-overlay"); if (mo) mo.addEventListener("click", closeAll);

    document.addEventListener("keydown", function (e) { if (e.key === "Escape") closeAll(); });
  }

  // ============================================================ ADD TO CART
  function wireAddToCart() {
    $all("[data-add-cart]").forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        Cart.add({
          slug: btn.getAttribute("data-slug"),
          name: btn.getAttribute("data-name"),
          price: btn.getAttribute("data-price"),
          image: btn.getAttribute("data-image"),
          qty: 1
        });
        renderDrawer();
        syncCheckout();
        toast("Added to cart — " + (btn.getAttribute("data-name") || "item"), "success");
      });
    });
  }

  // ============================================================ CAT SLIDER
  function wireSlider() {
    var track = $("#cat-track");
    if (!track) return;
    var prev = $(".cat-prev"), next = $(".cat-next");
    var step = function () { return Math.max(track.clientWidth * 0.7, 200); };
    if (prev) prev.addEventListener("click", function () { track.scrollBy({ left: -step(), behavior: "smooth" }); });
    if (next) next.addEventListener("click", function () { track.scrollBy({ left: step(), behavior: "smooth" }); });
  }

  // ============================================================ SORT (listing)
  function wireSort() {
    var sel = $("#sort-select"), grid = $("#product-grid");
    if (!sel || !grid) return;
    var original = Array.prototype.slice.call(grid.children);
    sel.addEventListener("change", function () {
      var cards = Array.prototype.slice.call(grid.children);
      var v = sel.value, sorted;
      if (v === "price-asc") sorted = cards.slice().sort(function (a, b) { return price(a) - price(b); });
      else if (v === "price-desc") sorted = cards.slice().sort(function (a, b) { return price(b) - price(a); });
      else if (v === "name") sorted = cards.slice().sort(function (a, b) { return name(a).localeCompare(name(b)); });
      else sorted = original;
      sorted.forEach(function (c) { grid.appendChild(c); });
    });
    function price(c) { return parseFloat(c.getAttribute("data-price")) || 0; }
    function name(c) { var n = c.querySelector(".card-name"); return n ? n.textContent.trim() : ""; }
  }

  // ============================================================ CHECKOUT
  function shippingFor(country, subtotal) {
    if (!country || country === DOMESTIC) {
      if (subtotal > 0 && subtotal >= CFG.freeShipThreshold) return 0;
      return subtotal > 0 ? CFG.flatShipping : 0;
    }
    return (CFG.freight && CFG.freight[country] != null) ? CFG.freight[country] : 0;
  }

  function syncCheckout() {
    var root = $("#checkout-form");
    if (!root) return;
    var wrap = $("#summary-items");
    var sub = Cart.subtotal();
    if (wrap) {
      if (!Cart.items.length) {
        wrap.innerHTML = '<div class="summary-empty">No items yet. <a href="/products">Browse products</a> to add some, or send us a general quote request below.</div>';
      } else {
        wrap.innerHTML = Cart.items.map(function (it) {
          return '' +
            '<div class="summary-item">' +
              '<img src="' + imgUrl(it.image) + '" alt="" onerror="this.onerror=null;this.src=\'/static/images/placeholder.jpg\';">' +
              '<div class="summary-item-info">' +
                '<div class="summary-item-name">' + escapeHtml(it.name) + '</div>' +
                '<div class="summary-item-meta">Qty ' + it.qty + ' × ' + money(it.price) + '</div>' +
              '</div>' +
              '<div class="summary-item-price">' + money(it.price * it.qty) + '</div>' +
            '</div>';
        }).join("");
      }
    }
    var country = ($("#country-select") || {}).value || DOMESTIC;
    var ship = shippingFor(country, sub);
    var subEl = $("#summary-subtotal"); if (subEl) subEl.textContent = money(sub);
    var shipEl = $("#summary-shipping");
    var shipLabel = $("#summary-ship-label");
    if (shipEl) shipEl.textContent = sub <= 0 ? "—" : (ship === 0 ? "FREE" : money(ship));
    if (shipLabel) shipLabel.textContent = (country && country !== DOMESTIC) ? "Est. freight" : "Shipping (est.)";
    var totEl = $("#summary-total"); if (totEl) totEl.textContent = money(sub + (sub > 0 ? ship : 0));
    var fr = $("#freight-region"); if (fr) fr.value = country;
  }

  function wireCheckout() {
    var form = $("#checkout-form");
    if (!form) return;

    // country -> freight region + state field visibility
    var country = $("#country-select");
    if (country) country.addEventListener("change", function () {
      var stateField = $("#state-field");
      if (stateField) stateField.classList.toggle("hidden", country.value !== DOMESTIC);
      syncCheckout();
    });

    // payment "Other" reveal
    $all('input[name="payment_method"]').forEach(function (r) {
      r.addEventListener("change", function () {
        var other = $("#payment-other-field");
        if (other) other.classList.toggle("hidden", $('input[name="payment_method"]:checked').value !== "Other");
      });
    });

    syncCheckout();

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var fd = new FormData(form);
      var payment = fd.get("payment_method") || "Bank Transfer";
      if (payment === "Other" && fd.get("payment_other")) payment = "Other: " + fd.get("payment_other");
      var country = fd.get("country") || DOMESTIC;
      var sub = Cart.subtotal();
      var ship = shippingFor(country, sub);
      var payload = {
        first_name: fd.get("first_name") || "", last_name: fd.get("last_name") || "",
        phone: fd.get("phone") || "", email: fd.get("email") || "",
        company: fd.get("company") || "", address: fd.get("address") || "",
        city: fd.get("city") || "", state: fd.get("state") || "",
        zip: fd.get("zip") || "", country: country,
        freight_region: country, contact_pref: fd.get("contact_pref") || "Phone Call",
        best_time: fd.get("best_time") || "", payment_method: payment,
        notes: fd.get("notes") || "",
        items: Cart.items.map(function (it) { return { slug: it.slug, name: it.name, price: it.price, qty: it.qty, image: it.image }; }),
        total: sub + (sub > 0 ? ship : 0)
      };
      var btn = $("#checkout-submit"); if (btn) { btn.disabled = true; btn.textContent = "Submitting…"; }
      postJSON("/api/inquiries", payload).then(function (res) {
        Cart.items = []; Cart.save(); updateCount();
        var rootWrap = $("#checkout-root"); if (rootWrap) rootWrap.classList.add("hidden");
        var ok = $("#checkout-success"); if (ok) { ok.classList.remove("hidden"); ok.scrollIntoView({ behavior: "smooth", block: "center" }); }
        toast((res && res.message) || "Request received!", "success");
      }).catch(function () {
        if (btn) { btn.disabled = false; btn.textContent = "Submit Request"; }
        toast("Something went wrong. Please call or email us instead.", "error");
      });
    });
  }

  // ============================================================ FINANCING CALC
  function wireFinancing() {
    var price = $("#calc-price");
    if (!price) return;
    var down = $("#calc-down"), apr = $("#calc-apr"), term = $("#calc-term");
    var aprVal = $("#calc-apr-val"), termVal = $("#calc-term-val");
    var moEl = $("#calc-monthly"), finEl = $("#calc-financed"), totEl = $("#calc-total"), intEl = $("#calc-interest");

    function calc() {
      var P = Math.max(0, (parseFloat(price.value) || 0) - (parseFloat(down.value) || 0));
      var annual = parseFloat(apr.value) || 0;
      var n = parseInt(term.value, 10) || 1;
      if (aprVal) aprVal.textContent = annual.toFixed(1);
      if (termVal) termVal.textContent = n;
      var r = annual / 100 / 12;
      var M;
      if (P <= 0) M = 0;
      else if (r === 0) M = P / n;
      else { var f = Math.pow(1 + r, n); M = P * r * f / (f - 1); }
      var total = M * n;
      if (moEl) moEl.textContent = money(Math.round(M));
      if (finEl) finEl.textContent = money(Math.round(P));
      if (totEl) totEl.textContent = money(Math.round(total));
      if (intEl) intEl.textContent = money(Math.max(0, Math.round(total - P)));
    }
    [price, down, apr, term].forEach(function (el) { if (el) { el.addEventListener("input", calc); el.addEventListener("change", calc); } });
    calc();
  }

  // ============================================================ FORM SUBMITS
  function bindBookingForm(formSel, successSel) {
    var form = $(formSel);
    if (!form) return;
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var fd = new FormData(form);
      var payload = {
        first_name: fd.get("first_name") || "", last_name: fd.get("last_name") || "",
        phone: fd.get("phone") || "", email: fd.get("email") || "",
        service: fd.get("service") || "General Inquiry",
        product_interest: fd.get("product_interest") || "",
        details: fd.get("details") || ""
      };
      var btn = form.querySelector('button[type="submit"]');
      var label = btn ? btn.textContent : "";
      if (btn) { btn.disabled = true; btn.textContent = "Sending…"; }
      postJSON("/api/bookings", payload).then(function (res) {
        form.reset();
        if (btn) { btn.disabled = false; btn.textContent = label; }
        if (successSel === "__modal__") {
          closePanel($("#quote-modal"), $("#quote-overlay"));
        } else {
          var ok = $(successSel);
          if (ok) { form.classList.add("hidden"); ok.classList.remove("hidden"); }
        }
        toast((res && res.message) || "Thanks! We'll be in touch shortly.", "success");
      }).catch(function () {
        if (btn) { btn.disabled = false; btn.textContent = label; }
        toast("Couldn't send right now. Please call or email us.", "error");
      });
    });
  }

  function postJSON(url, body) {
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    }).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json().catch(function () { return {}; });
    });
  }

  // ============================================================ TOAST
  var toastTimer;
  function toast(msg, type) {
    var c = $("#toast-container");
    if (!c) return;
    var el = document.createElement("div");
    el.className = "toast" + (type ? " " + type : "");
    el.textContent = msg;
    c.appendChild(el);
    requestAnimationFrame(function () { el.classList.add("show"); });
    setTimeout(function () {
      el.classList.remove("show");
      setTimeout(function () { if (el.parentNode) el.parentNode.removeChild(el); }, 350);
    }, 3200);
  }
  window.toast = toast;

  // ============================================================ INIT
  function init() {
    Cart.load();
    updateCount();
    renderDrawer();
    wireDrawer();
    wireOverlays();
    wireAddToCart();
    wireSlider();
    wireSort();
    wireCheckout();
    wireFinancing();
    bindBookingForm("#quote-form", "__modal__");
    bindBookingForm("#financing-form", "#financing-success");
    bindBookingForm("#contact-form", "#contact-success");
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
