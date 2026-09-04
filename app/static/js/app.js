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
