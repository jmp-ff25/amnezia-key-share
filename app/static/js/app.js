document.querySelectorAll('.copy-button').forEach((button) => {
  button.addEventListener('click', async () => {
    const target = document.getElementById(button.dataset.copyTarget);
    const text = target.value || target.textContent;
    let copied = false;
    try { if (navigator.clipboard && window.isSecureContext) { await navigator.clipboard.writeText(text); copied = true; } } catch (_) {}
    if (!copied) { target.focus(); target.select(); target.setSelectionRange(0, text.length); copied = document.execCommand('copy'); }
    if (copied) { const label = button.querySelector('span'); const previous = label.textContent; label.textContent = 'Скопировано'; button.classList.add('copy-success'); setTimeout(() => { label.textContent = previous; button.classList.remove('copy-success'); }, 2200); }
  });
});
document.querySelectorAll('form[data-confirm]').forEach((form) => form.addEventListener('submit', (event) => { if (!window.confirm(form.dataset.confirm)) event.preventDefault(); }));

const keyList = document.getElementById('key-list');
const addKey = document.getElementById('add-key');
if (keyList && addKey) {
  const refreshKeyControls = () => {
    const rows = keyList.querySelectorAll('.key-editor');
    rows.forEach((row) => { row.querySelector('.remove-key').disabled = rows.length === 1; });
    addKey.disabled = rows.length >= 20;
  };
  addKey.addEventListener('click', () => {
    const template = document.getElementById('key-editor-template');
    keyList.appendChild(template.content.cloneNode(true));
    keyList.lastElementChild.querySelector('input[name="key_name"]').focus();
    refreshKeyControls();
  });
  keyList.addEventListener('click', (event) => {
    const button = event.target.closest('.remove-key');
    if (button && keyList.children.length > 1) {
      button.closest('.key-editor').remove();
      refreshKeyControls();
    }
  });
  refreshKeyControls();
}

const publicKeyList = document.getElementById('public-key-list');
if (publicKeyList) {
  const layoutButtons = document.querySelectorAll('[data-layout]');
  const setLayout = (layout) => {
    publicKeyList.classList.toggle('layout-grid', layout === 'grid');
    publicKeyList.classList.toggle('layout-list', layout === 'list');
    layoutButtons.forEach((button) => {
      const active = button.dataset.layout === layout;
      button.classList.toggle('active', active);
      button.setAttribute('aria-pressed', String(active));
    });
  };
  const preferred = localStorage.getItem('keyport-key-layout');
  setLayout(preferred === 'list' || preferred === 'grid' ? preferred : 'grid');
  layoutButtons.forEach((button) => button.addEventListener('click', () => {
    localStorage.setItem('keyport-key-layout', button.dataset.layout);
    setLayout(button.dataset.layout);
  }));
}

if ('serviceWorker' in navigator) navigator.serviceWorker.register('/service-worker.js');
let installPrompt;
window.addEventListener('beforeinstallprompt', (event) => { event.preventDefault(); installPrompt = event; });
document.getElementById('install-app')?.addEventListener('click', async () => {
  if (installPrompt) { installPrompt.prompt(); await installPrompt.userChoice; installPrompt = null; return; }
  const ios = /iphone|ipad|ipod/i.test(navigator.userAgent);
  window.alert(ios ? 'Откройте ссылку в Safari, нажмите «Поделиться» и выберите «На экран Домой».' : 'Откройте меню браузера и выберите «Установить приложение» или «Добавить на главный экран».');
});
