/* Student-scoped IndexedDB packages and acknowledged, idempotent commands.
   API responses and credentials never enter service-worker CacheStorage. */
import api from './api';
const DB = 'classpulse-learning-v1';
function openDb() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB, 1);
    request.onupgradeneeded = () => {
      const db = request.result;
      db.createObjectStore('packages', { keyPath: 'key' });
      db.createObjectStore('queue', { keyPath: 'key' });
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}
async function transact(store, mode, action) {
  const db = await openDb();
  try {
    return await new Promise((resolve, reject) => {
      const tx = db.transaction(store, mode);
      const request = action(tx.objectStore(store));
      tx.oncomplete = () => resolve(request.result);
      tx.onerror = () => reject(tx.error);
      tx.onabort = () => reject(tx.error || new Error('Local storage unavailable'));
    });
  } finally { db.close(); }
}
export async function savePackage(owner, kind, item) {
  const record = { key: `${owner}:${kind}:${item.id}`, owner, kind, item, downloadedAt: new Date().toISOString() };
  await transact('packages', 'readwrite', (s) => s.put(record));
  return record;
}
export async function offlinePackages(owner) {
  return (await transact('packages', 'readonly', (s) => s.getAll())).filter((p) => p.owner === owner);
}
export async function queuedCommands(owner) {
  return (await transact('queue', 'readonly', (s) => s.getAll())).filter((p) => p.owner === owner);
}
export async function queuePractice(owner, assignment, answers) {
  const id = crypto.randomUUID();
  const item = { key: id, owner, assignmentId: assignment.id, status: 'pending', attempts: 0, nextAttemptAt: 0,
    payload: { request_id: id, intervention_id: assignment.intervention_id, answers } };
  await transact('queue', 'readwrite', (s) => s.put(item));
  return item;
}
let syncing = false;
export async function synchronize(owner, force = false) {
  if (syncing || !navigator.onLine) return;
  syncing = true;
  try {
    const queue = (await queuedCommands(owner)).filter((c) => c.status !== 'synchronized' && c.status !== 'conflict' && (force || c.nextAttemptAt <= Date.now())).slice(0, 10);
    for (const command of queue) {
      try {
        const result = (await api.post(`/intervention-assignments/${command.assignmentId}/sync-practice`, command.payload)).data;
        command.status = 'synchronized'; command.result = result;
      } catch (error) {
        const status = error.response?.status;
        command.status = status === 409 || status === 422 || status === 403 ? 'conflict' : status === 401 ? 'sign_in_required' : 'pending';
        command.attempts += 1;
        command.nextAttemptAt = Date.now() + Math.min(3600000, 2000 * 2 ** Math.min(command.attempts, 10));
        command.error = status ? `HTTP ${status}` : 'Connection unavailable';
      }
      await transact('queue', 'readwrite', (s) => s.put(command));
      if (command.status === 'sign_in_required') break;
    }
  } finally { syncing = false; }
}
export async function assertOfflineCanLogout() {
  if (!globalThis.indexedDB) return;
  const pending = (await transact('queue', 'readonly', (s) => s.getAll())).some((c) => c.status !== 'synchronized');
  if (pending) throw new Error('PENDING_OFFLINE_RESPONSES');
}
export async function clearOfflineData() {
  if (!globalThis.indexedDB) return;
  await assertOfflineCanLogout();
  await transact('packages', 'readwrite', (s) => s.clear());
  await transact('queue', 'readwrite', (s) => s.clear());
}
