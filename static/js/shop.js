/* Клубок — невеликі покращення UX. Усі форми працюють і без JS. */
(function () {
  'use strict';

  /* ---- Лістинг: декоративні чіпи-фільтри (як у прототипі) ---- */
  document.querySelectorAll('.filters').forEach(function (group) {
    group.querySelectorAll('.chip').forEach(function (chip) {
      chip.addEventListener('click', function () {
        group.querySelectorAll('.chip').forEach(function (c) { c.classList.remove('on'); });
        chip.classList.add('on');
      });
    });
  });

  /* ---- Авто-сабміт сортування ---- */
  var sortSelect = document.querySelector('.sort[data-autosubmit]');
  if (sortSelect) {
    sortSelect.addEventListener('change', function () {
      var url = new URL(window.location.href);
      url.searchParams.set('sort', sortSelect.value);
      url.searchParams.delete('page'); // нове сортування -> з першої сторінки
      window.location.href = url.toString();
    });
  }

  /* ---- Кошик: підтвердження видалення товару ---- */
  var removeModal = document.getElementById('removeModal');
  if (removeModal) {
    var pendingForm = null;
    var removeText = document.getElementById('removeText');
    var closeRemove = function () { removeModal.hidden = true; pendingForm = null; };

    document.querySelectorAll('[data-confirm-remove]').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.preventDefault();   // без JS кнопка-submit видаляє одразу; з JS — спершу підтвердження
        pendingForm = btn.closest('form');
        if (btn.dataset.name) {
          removeText.textContent = 'Прибрати «' + btn.dataset.name + '» з кошика?';
        }
        removeModal.hidden = false;
      });
    });

    var confirmBtn = document.getElementById('removeConfirm');
    if (confirmBtn) confirmBtn.addEventListener('click', function () {
      if (pendingForm) pendingForm.submit();
    });
    removeModal.querySelectorAll('[data-modal-cancel]').forEach(function (x) {
      x.addEventListener('click', closeRemove);
    });
    removeModal.addEventListener('click', function (e) {
      if (e.target === removeModal) closeRemove();   // клік по тлу
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && !removeModal.hidden) closeRemove();
    });
  }

  /* ---- Сторінка товару ---- */
  var pf = document.getElementById('product-form');
  if (pf) {
    var qInput = pf.querySelector('#q');
    var sizeField = pf.querySelector('#size-field');
    var colorField = pf.querySelector('#color-field');
    var sizeVal = document.getElementById('sizeVal');
    var colorVal = document.getElementById('colorVal');

    pf.querySelectorAll('.qty button[data-step]').forEach(function (b) {
      b.addEventListener('click', function () {
        var v = Math.max(1, (parseInt(qInput.value, 10) || 1) + parseInt(b.dataset.step, 10));
        qInput.value = v;
      });
    });

    pf.querySelectorAll('#sizes .ob').forEach(function (b) {
      b.addEventListener('click', function () {
        pf.querySelectorAll('#sizes .ob').forEach(function (o) { o.classList.remove('on'); });
        b.classList.add('on');
        if (sizeField) sizeField.value = b.dataset.v;
        if (sizeVal) sizeVal.textContent = b.dataset.v;
      });
    });

    pf.querySelectorAll('#colors .sw').forEach(function (b) {
      b.addEventListener('click', function () {
        pf.querySelectorAll('#colors .sw').forEach(function (o) { o.classList.remove('on'); });
        b.classList.add('on');
        if (colorField) colorField.value = b.dataset.v;
        if (colorVal) colorVal.textContent = b.dataset.v;
      });
    });

    /* Галерея: перемикання головного зображення */
    var mainImg = document.getElementById('mainImg');
    document.querySelectorAll('.thumbs .thumb').forEach(function (t) {
      t.addEventListener('click', function () {
        document.querySelectorAll('.thumbs .thumb').forEach(function (x) { x.classList.remove('on'); });
        t.classList.add('on');
        if (mainImg && t.dataset.media) mainImg.innerHTML = t.dataset.media;
      });
    });
  }

  /* ---- Оформлення: перемикання способу оплати ----
     (логіка доставки + Нова Пошта живе в novaposhta.js) */
  var payment = document.getElementById('payment');
  if (payment) {
    payment.querySelectorAll('.ro').forEach(function (r) {
      r.addEventListener('click', function () {
        payment.querySelectorAll('.ro').forEach(function (o) { o.classList.remove('on'); });
        r.classList.add('on');
        var radio = r.querySelector('input[type=radio]');
        if (radio) radio.checked = true;
      });
    });
  }
})();
