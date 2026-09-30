import { Editor } from '@tiptap/core';
import { StarterKit } from '@tiptap/starter-kit';
import { Image } from '@tiptap/extension-image';
import { FileHandler } from '@tiptap/extension-file-handler';
import { Color } from '@tiptap/extension-color';
import { FontFamily } from '@tiptap/extension-font-family';
import { TextStyle } from '@tiptap/extension-text-style';
import { TextAlign } from '@tiptap/extension-text-align';

const form = document.getElementById('access-form');
const editors = new Map();
let pendingUploads = 0;

const toolbarMarkup = `
  <select data-action="heading" aria-label="Заголовок"><option value="paragraph">Текст</option><option value="h2">Заголовок</option><option value="h3">Подзаголовок</option></select>
  <span class="toolbar-divider"></span>
  <button type="button" data-action="bold" title="Жирный" aria-label="Жирный"><strong>Ж</strong></button>
  <button type="button" data-action="italic" title="Курсив" aria-label="Курсив"><em>К</em></button>
  <button type="button" data-action="underline" title="Подчёркнутый" aria-label="Подчёркнутый"><u>Ч</u></button>
  <span class="toolbar-divider"></span>
  <button type="button" data-action="bullet" title="Маркированный список" aria-label="Маркированный список">•</button>
  <button type="button" data-action="ordered" title="Нумерованный список" aria-label="Нумерованный список">1.</button>
  <button type="button" data-action="quote" title="Цитата" aria-label="Цитата">❝</button>
  <span class="toolbar-divider"></span>
  <button type="button" data-action="link" title="Ссылка" aria-label="Ссылка">🔗</button>
  <button type="button" data-action="image" title="Загрузить картинку или GIF" aria-label="Загрузить картинку или GIF">🖼</button>
  <span class="toolbar-divider"></span>
  <select data-action="font" aria-label="Шрифт"><option value="">Шрифт</option><option value="Georgia, serif">С засечками</option><option value="monospace">Моноширинный</option></select>
  <input type="color" class="toolbar-color" data-action="color" value="#25263b" title="Цвет текста" aria-label="Цвет текста">
  <button type="button" data-action="undo" title="Отменить" aria-label="Отменить">↶</button>
  <button type="button" data-action="redo" title="Повторить" aria-label="Повторить">↷</button>
`;

function showError(wrapper, message) {
  wrapper.querySelector('.rich-editor-feedback').textContent = message;
}

async function uploadImage(file, editor, wrapper) {
  if (!file) return;
  if (!['image/png', 'image/jpeg', 'image/webp', 'image/gif'].includes(file.type)) {
    showError(wrapper, 'Разрешены PNG, JPEG, WebP и GIF.');
    return;
  }
  if (file.size > 5 * 1024 * 1024) {
    showError(wrapper, 'Файл должен быть не больше 5 МБ.');
    return;
  }
  const feedback = wrapper.querySelector('.rich-editor-feedback');
  feedback.textContent = 'Загружаем изображение…';
  pendingUploads += 1;
  const body = new FormData();
  body.append('image', file);
  body.append('csrf_token', form.querySelector('[name="csrf_token"]').value);
  try {
    const response = await fetch(form.dataset.uploadUrl, { method: 'POST', body, credentials: 'same-origin' });
    const result = await response.json();
    if (!response.ok || !result.url) throw new Error(result.error || 'Не удалось загрузить изображение.');
    editor.chain().focus().setImage({ src: result.url, alt: file.name }).run();
    feedback.textContent = '';
  } catch (error) {
    showError(wrapper, error.message || 'Не удалось загрузить изображение.');
  } finally {
    pendingUploads -= 1;
  }
}

function updateToolbar(wrapper, editor) {
  for (const [action, mark] of Object.entries({
    bold: 'bold', italic: 'italic', underline: 'underline',
    bullet: 'bulletList', ordered: 'orderedList', quote: 'blockquote',
  })) {
    wrapper.querySelector(`[data-action="${action}"]`).classList.toggle('is-active', editor.isActive(mark));
  }
  const heading = wrapper.querySelector('[data-action="heading"]');
  heading.value = editor.isActive('heading', { level: 2 }) ? 'h2' : editor.isActive('heading', { level: 3 }) ? 'h3' : 'paragraph';
}

function editorHtml(editor) {
  const hasImage = editor.getJSON().content?.some((node) => node.type === 'image');
  return editor.getText().trim() || hasImage ? editor.getHTML() : '';
}

function initEditor(wrapper) {
  if (editors.has(wrapper)) return;
  const source = wrapper.querySelector('.rich-source');
  const surface = wrapper.querySelector('.rich-surface');
  const toolbar = wrapper.querySelector('.rich-toolbar');
  toolbar.innerHTML = toolbarMarkup;
  const editor = new Editor({
    element: surface,
    extensions: [
      StarterKit,
      Image.configure({ allowBase64: false }),
      TextStyle, Color, FontFamily,
      TextAlign.configure({ types: ['heading', 'paragraph'] }),
      FileHandler.configure({
        allowedMimeTypes: ['image/png', 'image/jpeg', 'image/webp', 'image/gif'],
        consumePasteEvent: true,
        onPaste: (currentEditor, files) => uploadImage(files[0], currentEditor, wrapper),
        onDrop: (currentEditor, files, pos) => {
          currentEditor.chain().focus().setTextSelection(pos).run();
          uploadImage(files[0], currentEditor, wrapper);
        },
      }),
    ],
    content: source.value || '<p></p>',
    editorProps: { attributes: { 'aria-label': wrapper.dataset.label } },
    onUpdate: ({ editor: currentEditor }) => {
      source.value = editorHtml(currentEditor);
      updateToolbar(wrapper, currentEditor);
    },
    onSelectionUpdate: ({ editor: currentEditor }) => updateToolbar(wrapper, currentEditor),
  });
  editors.set(wrapper, editor);
  wrapper.classList.add('is-ready');
  surface.hidden = false;
  updateToolbar(wrapper, editor);

  const fileInput = document.createElement('input');
  fileInput.type = 'file';
  fileInput.accept = 'image/png,image/jpeg,image/webp,image/gif';
  fileInput.hidden = true;
  wrapper.appendChild(fileInput);
  fileInput.addEventListener('change', () => {
    uploadImage(fileInput.files?.[0], editor, wrapper);
    fileInput.value = '';
  });

  toolbar.addEventListener('click', (event) => {
    const action = event.target.closest('button[data-action]')?.dataset.action;
    if (!action) return;
    const chain = editor.chain().focus();
    if (action === 'bold') chain.toggleBold().run();
    if (action === 'italic') chain.toggleItalic().run();
    if (action === 'underline') chain.toggleUnderline().run();
    if (action === 'bullet') chain.toggleBulletList().run();
    if (action === 'ordered') chain.toggleOrderedList().run();
    if (action === 'quote') chain.toggleBlockquote().run();
    if (action === 'undo') chain.undo().run();
    if (action === 'redo') chain.redo().run();
    if (action === 'image') fileInput.click();
    if (action === 'link') {
      const previous = editor.getAttributes('link').href || 'https://';
      const href = window.prompt('Адрес ссылки (https://...)', previous)?.trim();
      if (href === undefined) return;
      if (!/^https?:\/\//i.test(href)) {
        showError(wrapper, 'Ссылка должна начинаться с https:// или http://');
        return;
      }
      chain.extendMarkRange('link').setLink({ href }).run();
    }
    updateToolbar(wrapper, editor);
  });
  toolbar.addEventListener('change', (event) => {
    const action = event.target.dataset.action;
    if (action === 'heading') {
      const value = event.target.value;
      if (value === 'paragraph') editor.chain().focus().setParagraph().run();
      else editor.chain().focus().toggleHeading({ level: Number(value.slice(1)) }).run();
    }
    if (action === 'font') {
      const value = event.target.value;
      if (value) editor.chain().focus().setFontFamily(value).run();
      else editor.chain().focus().unsetFontFamily().run();
    }
    if (action === 'color') editor.chain().focus().setColor(event.target.value).run();
  });
}

if (form) {
  form.querySelectorAll('[data-rich-editor]').forEach(initEditor);
  document.addEventListener('keyport:key-added', (event) => {
    event.detail.row.querySelectorAll('[data-rich-editor]').forEach(initEditor);
  });
  document.addEventListener('keyport:key-removing', (event) => {
    event.detail.row.querySelectorAll('[data-rich-editor]').forEach((wrapper) => {
      editors.get(wrapper)?.destroy();
      editors.delete(wrapper);
    });
  });
  form.addEventListener('submit', (event) => {
    if (pendingUploads) {
      event.preventDefault();
      window.alert('Подождите, пока загрузится изображение, затем сохраните ещё раз.');
      return;
    }
    for (const [wrapper, editor] of editors) {
      wrapper.querySelector('.rich-source').value = editorHtml(editor);
    }
  });
}
