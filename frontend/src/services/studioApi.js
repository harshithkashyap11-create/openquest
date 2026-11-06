import api from './api';

export const questionKinds = ['choice', 'multiple_select', 'true_false', 'numeric', 'short_answer', 'writing', 'matching', 'categorize'];

export function newQuestion(kind = 'choice') {
  return { id: crypto.randomUUID(), kind, text: '', options: ['choice', 'multiple_select', 'true_false'].includes(kind) ? kind === 'true_false' ? ['True', 'False'] : ['', '', '', ''] : ['matching', 'categorize'].includes(kind) ? ['Group 1', 'Group 2'] : [], items: [], answer: kind === 'multiple_select' ? [0] : ['choice', 'true_false'].includes(kind) ? 0 : ['matching', 'categorize'].includes(kind) ? {} : kind === 'writing' ? null : '', explanation: '', hint: '', standard: '', points: 1, distractors: {} };
}

export async function downloadFile(url, name) {
  const { data } = await api.get(url, { responseType: 'blob' });
  const object = URL.createObjectURL(data); const a = document.createElement('a'); a.href = object; a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(object), 1000);
}
