/* Тема и фильтр разделов. Ванильно и без зависимостей — страница должна
   открываться и работать даже если скрипт не загрузился. */
(function () {
  'use strict';

  // ── тема ────────────────────────────────────────────────────────────────
  var btn = document.getElementById('theme');
  if (btn) {
    var системная = function () {
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    };
    var подпись = function () {
      var t = document.documentElement.getAttribute('data-theme') || системная();
      btn.textContent = t === 'dark' ? '☀' : '☾';
      btn.setAttribute('aria-label',
        t === 'dark' ? 'Включить светлую тему' : 'Включить тёмную тему');
    };
    подпись();
    btn.addEventListener('click', function () {
      var сейчас = document.documentElement.getAttribute('data-theme') || системная();
      var новая = сейчас === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', новая);
      try { localStorage.setItem('theme', новая); } catch (e) {}
      подпись();
    });
  }

  // ── фильтр разделов ─────────────────────────────────────────────────────
  var панель = document.querySelector('.filters');
  var список = document.getElementById('rows');
  if (панель && список) {
    var счётчик = document.getElementById('shown');
    var применить = function (раздел) {
      var видно = 0;
      Array.prototype.forEach.call(список.children, function (row) {
        var подходит = !раздел || row.getAttribute('data-section') === раздел;
        row.hidden = !подходит;
        if (подходит) видно++;
      });
      if (счётчик) счётчик.textContent = видно;
    };
    панель.addEventListener('click', function (e) {
      var b = e.target.closest('button');
      if (!b) return;
      Array.prototype.forEach.call(панель.querySelectorAll('button'), function (x) {
        x.classList.toggle('on', x === b);
      });
      применить(b.getAttribute('data-filter') || '');
    });
  }

  // ── раскрыть тему по якорю ──────────────────────────────────────────────
  // Ссылка вида pains.html#t-42 должна не просто прокрутить, а открыть строку.
  var раскрыть = function () {
    var id = location.hash.slice(1);
    if (!id) return;
    var el = document.getElementById(id);
    if (el && el.tagName === 'DETAILS') {
      el.open = true;
      el.scrollIntoView({ block: 'start' });
    }
  };
  window.addEventListener('hashchange', раскрыть);
  раскрыть();
})();
