// axis_saas/static/js/offline_student.js
// Offline student creation with IndexedDB sync

(function() {
    'use strict';

    const DB_NAME = 'AxisOfflineDB';
    const STORE_NAME = 'offlineStudents';
    const DB_VERSION = 1;

    let db = null;

    function openDB() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(DB_NAME, DB_VERSION);
            request.onupgradeneeded = (ev) => {
                const db = ev.target.result;
                if (!db.objectStoreNames.contains(STORE_NAME)) {
                    db.createObjectStore(STORE_NAME, { keyPath: 'id', autoIncrement: true });
                }
            };
            request.onsuccess = (ev) => resolve(ev.target.result);
            request.onerror = (ev) => reject(ev.target.error);
        });
    }

    async function getDB() {
        if (!db) db = await openDB();
        return db;
    }

    async function saveOfflineStudent(data) {
        const db = await getDB();
        return new Promise((resolve, reject) => {
            const tx = db.transaction(STORE_NAME, 'readwrite');
            const store = tx.objectStore(STORE_NAME);
            const request = store.add(data);
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    async function getOfflineStudents() {
        const db = await getDB();
        return new Promise((resolve, reject) => {
            const tx = db.transaction(STORE_NAME, 'readonly');
            const store = tx.objectStore(STORE_NAME);
            const request = store.getAll();
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    async function deleteOfflineStudent(id) {
        const db = await getDB();
        return new Promise((resolve, reject) => {
            const tx = db.transaction(STORE_NAME, 'readwrite');
            const store = tx.objectStore(STORE_NAME);
            const request = store.delete(id);
            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
        });
    }

    function parseOfflineAction(form) {
        const actionUrl = form.getAttribute('action') || window.location.href;
        const editMatch = actionUrl.match(/\/students\/edit\/(\d+)\/?$/);
        return {
            action: editMatch ? 'edit' : 'create',
            student_id: editMatch ? editMatch[1] : null,
            action_url: actionUrl
        };
    }

    async function queueStudentSubmission(item) {
        return saveOfflineStudent(item);
    }

    async function submitStudentForm(form, redirectUrl = '') {
        if (!form) return false;

        const payload = Object.fromEntries(new FormData(form).entries());
        const offlineMeta = parseOfflineAction(form);
        const actionUrl = offlineMeta.action_url;

        try {
            const response = await fetch(actionUrl, {
                method: 'POST',
                body: new FormData(form),
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': getCsrfToken()
                },
                credentials: 'same-origin'
            });

            if (response.ok || response.redirected) {
                const targetUrl = response.url || redirectUrl || actionUrl;
                window.location.assign(targetUrl);
                return true;
            }

            throw new Error(`Server returned ${response.status}`);
        } catch (error) {
            if (typeof window !== 'undefined' && window.offlineStudent?.save) {
                const offlineItem = {
                    action: offlineMeta.action,
                    student_id: offlineMeta.student_id,
                    data: payload,
                    submitted_at: new Date().toISOString(),
                    redirect_to: redirectUrl,
                    action_url: actionUrl
                };
                await queueStudentSubmission(offlineItem);
                const message = offlineMeta.action === 'edit'
                    ? 'Student update saved offline. It will sync automatically when the connection returns.'
                    : 'Student saved offline. It will sync automatically when the connection returns.';
                if (window.offlineStudent?.notify) {
                    window.offlineStudent.notify(message);
                } else {
                    alert(message);
                }
                if (redirectUrl) {
                    window.location.assign(redirectUrl);
                }
                return true;
            }

            console.error('Could not save student offline', error);
            alert('Could not save student offline. Please try again.');
            return false;
        }
    }

    function isStudentListPage() {
        if (typeof window === 'undefined') return false;
        const path = window.location.pathname || '';
        return /\/portal\/[^/]+\/students\/(?:mobile\/)?$/.test(path);
    }

    function isStudentProfilePage() {
        if (typeof window === 'undefined') return false;
        const path = window.location.pathname || '';
        return /\/portal\/[^/]+\/students\/(?:mobile\/)?\d+\/?$/.test(path);
    }

    function getCurrentStudentId() {
        const path = window.location.pathname || '';
        const match = path.match(/\/students\/(?:mobile\/)?(\d+)\/?$/);
        return match ? match[1] : null;
    }

    function renderOfflineBanner(count) {
        const existing = document.querySelector('.offline-sync-banner');
        if (existing) existing.remove();
        const banner = document.createElement('div');
        banner.className = 'offline-sync-banner';
        banner.style.cssText = 'margin-bottom:1rem;padding:0.9rem 1rem;border-radius:0.75rem;background:#fef3c7;color:#92400e;font-size:0.95rem;font-weight:600;border:1px solid #fde68a;';
        banner.textContent = `You have ${count} offline student change${count === 1 ? '' : 's'} pending sync.`;
        const target = document.querySelector('.table-card, .student-list, .profile-header');
        if (target) {
            target.parentNode.insertBefore(banner, target);
        }
    }

    function buildPendingRow(item) {
        const data = item.data || {};
        const row = document.createElement('tr');
        row.dataset.offlineId = item.id;
        row.innerHTML = `
            <td><span class="roll-badge">${data.roll_number || 'TBD'}</span></td>
            <td><strong>${data.name || 'Offline Student'}</strong> <span style="display:inline-block;margin-left:0.5rem;padding:0.15rem 0.55rem;border-radius:999px;background:#fef3c7;color:#92400e;font-size:0.7rem;font-weight:700;">Pending sync</span></td>
            <td>${data.father_name || '—'}</td>
            <td>${data.grade || '—'} - ${data.section || '—'}</td>
            <td><span class="fee-pending">₹0.00</span></td>
            <td><span class="status-badge" style="background:#fde68a;color:#92400e;">Offline</span></td>
            <td class="action-btns">—</td>
        `;
        return row;
    }

    function buildPendingCard(item) {
        const data = item.data || {};
        const card = document.createElement('div');
        card.className = 'student-card offline-pending-card';
        card.dataset.offlineId = item.id;
        card.innerHTML = `
            <div class="card-top">
                <div class="student-name">${data.name || 'Offline Student'}</div>
                <span class="badge badge-offline">Pending sync</span>
            </div>
            <div class="student-meta">${data.grade || '—'}<span class="separator">•</span>${data.section || '—'}<span class="separator">•</span>Roll ${data.roll_number || 'TBD'}</div>
            <div class="student-father">${data.father_name || '—'}</div>
            <div class="student-actions"><span style="color:#92400e;font-weight:700;">Offline pending</span></div>
        `;
        return card;
    }

    async function renderPendingQueue() {
        try {
            const queue = await getOfflineStudents();
            console.log('[Offline] renderPendingQueue called, items:', queue.length);
            if (!queue.length) {
                console.log('[Offline] No pending items to render');
                return;
            }
            
            renderOfflineBanner(queue.length);

            if (isStudentListPage()) {
                console.log('[Offline] On student list page, attempting to render', queue.length, 'pending students');
                
                // Desktop table
                const tableBody = document.querySelector('.data-table tbody');
                console.log('[Offline] .data-table tbody:', tableBody ? '✓ FOUND' : '✗ NOT FOUND');
                
                if (tableBody) {
                    let addedCount = 0;
                    queue.forEach(item => {
                        const action = item.action || 'create';
                        if (action === 'create') {
                            const existing = document.querySelector(`tr[data-offline-id='${item.id}']`);
                            if (!existing) {
                                const row = buildPendingRow(item);
                                tableBody.prepend(row);
                                addedCount++;
                                console.log('[Offline] ✓ Prepended to desktop:', item.data.name);
                            }
                        }
                    });
                    console.log('[Offline] Desktop: Added', addedCount, 'pending students');
                }
                
                // Mobile list
                const mobileContainer = document.getElementById('studentContainer');
                console.log('[Offline] #studentContainer:', mobileContainer ? '✓ FOUND' : '✗ NOT FOUND');
                
                if (mobileContainer) {
                    let addedCount = 0;
                    queue.forEach(item => {
                        const action = item.action || 'create';
                        if (action === 'create') {
                            const existing = document.querySelector(`.student-card[data-offline-id='${item.id}']`);
                            if (!existing) {
                                const card = buildPendingCard(item);
                                mobileContainer.prepend(card);
                                addedCount++;
                                console.log('[Offline] ✓ Prepended to mobile:', item.data.name);
                            }
                        }
                    });
                    console.log('[Offline] Mobile: Added', addedCount, 'pending students');
                }
                
                if (!tableBody && !mobileContainer) {
                    console.warn('[Offline] ⚠️  Neither .data-table tbody nor #studentContainer found!');
                    console.warn('[Offline] Possible causes: (1) Service worker not serving cached list page, (2) offline_student.js loaded before DOM ready, (3) This is not a list page');
                    console.warn('[Offline] URL:', window.location.href);
                    console.warn('[Offline] Page body available:', !!document.body);
                }
                
                // Handle edits
                queue.forEach(item => {
                    const action = item.action || 'create';
                    if (action === 'edit' && item.student_id) {
                        const desktopRow = document.querySelector(`tr[data-student-id='${item.student_id}']`);
                        if (desktopRow) {
                            desktopRow.querySelector('td:nth-child(2)').innerHTML = `<strong>${item.data.name || desktopRow.querySelector('td:nth-child(2)').textContent}</strong> <span style="display:inline-block;margin-left:0.5rem;padding:0.15rem 0.55rem;border-radius:999px;background:#fef3c7;color:#92400e;font-size:0.7rem;font-weight:700;">Edit pending</span>`;
                            console.log('[Offline] ✓ Marked edit pending on:', item.data.name);
                        }
                    }
                });
            }

            if (isStudentProfilePage()) {
                const studentId = getCurrentStudentId();
                const pendingEdits = queue.filter(item => item.action === 'edit' && String(item.student_id) === String(studentId));
                if (pendingEdits.length) {
                    const message = pendingEdits.length === 1
                        ? 'This student has an offline edit pending sync.'
                        : `This student has ${pendingEdits.length} offline changes pending sync.`;
                    const banner = document.createElement('div');
                    banner.className = 'offline-sync-banner';
                    banner.style.cssText = 'margin-bottom:1rem;padding:0.9rem 1rem;border-radius:0.75rem;background:#fef3c7;color:#92400e;font-size:0.95rem;font-weight:600;border:1px solid #fde68a;';
                    banner.textContent = message;
                    const header = document.querySelector('.profile-header');
                    if (header) header.parentNode.insertBefore(banner, header.nextSibling);
                    console.log('[Offline] ✓ Showed profile edit pending banner');
                }
            }
        } catch (err) {
            console.error('[Offline] Error rendering pending queue:', err);
        }
    }

    function refreshStudentListPage() {
        if (!isStudentListPage()) return;
        const url = new URL(window.location.href);
        url.searchParams.set('__offline_sync', Date.now().toString());
        window.location.replace(url.toString());
    }

    // Sync function: send all offline students to server
    async function syncOfflineStudents() {
        if (!navigator.onLine) return;
        const students = await getOfflineStudents();
        if (students.length === 0) return;

        let shouldRefreshList = false;

        // Get schema from window variable or from URL
        let schema = window.AXIS_SCHEMA || '';
        if (!schema) {
            // Fallback: extract from URL path
            const pathParts = window.location.pathname.split('/');
            if (pathParts.length >= 3 && pathParts[1] === 'portal') {
                schema = pathParts[2];
            }
        }
        if (!schema) {
            console.warn('No tenant schema found, cannot sync');
            return;
        }

        for (const student of students) {
            try {
                const resp = await fetch(`/portal/${schema}/api/sync-offline-student/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCsrfToken()
                    },
                    body: JSON.stringify(student.data)
                });
                if (resp.ok) {
                    await deleteOfflineStudent(student.id);
                    shouldRefreshList = true;
                    clearPendingListState();
                    showToast('✅ Student synced: ' + student.data.name);
                } else {
                    const errorText = await resp.text();
                    console.error('Sync failed for student', student.data.name, errorText);
                }
            } catch (e) {
                console.error('Sync error:', e);
            }
        }

        if (shouldRefreshList) {
            setTimeout(refreshStudentListPage, 800);
        }
    }

    function getCsrfToken() {
        const cookie = document.cookie.split('; ').find(row => row.startsWith('csrftoken='));
        return cookie ? cookie.split('=')[1] : '';
    }

    // Toast notification (improved)
    function showToast(msg) {
        const existing = document.querySelector('.offline-toast');
        if (existing) existing.remove();

        const toast = document.createElement('div');
        toast.className = 'offline-toast';
        toast.style.cssText = `
            position: fixed;
            bottom: 100px;
            left: 50%;
            transform: translateX(-50%);
            background: #10b981;
            color: white;
            padding: 12px 24px;
            border-radius: 30px;
            font-weight: 600;
            z-index: 9999;
            box-shadow: 0 8px 24px rgba(0,0,0,0.2);
            animation: fadeInUp 0.4s ease;
            max-width: 90%;
            text-align: center;
            font-size: 0.95rem;
        `;
        toast.textContent = msg;
        document.body.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transition = 'opacity 0.3s';
            setTimeout(() => toast.remove(), 400);
        }, 4000);
    }

    // Expose functions globally
    window.offlineStudent = {
        save: saveOfflineStudent,
        sync: syncOfflineStudents,
        getPending: getOfflineStudents,
        notify: showToast,
        queue: queueStudentSubmission,
        submitForm: submitStudentForm
    };

    // Auto-sync when online
    window.addEventListener('online', () => {
        syncOfflineStudents();
    });

    // Also sync on page load if online or if there are pending offline items
    document.addEventListener('DOMContentLoaded', async () => {
        console.log('[Offline] DOMContentLoaded fired');
        await renderPendingQueue();
        if (navigator.onLine) {
            console.log('[Offline] Online, starting sync in 3 seconds');
            setTimeout(syncOfflineStudents, 3000);
        } else {
            console.log('[Offline] Offline mode detected');
        }
    });

    // Check for pending students and show a badge (optional)
    async function showPendingBadge() {
        const students = await getOfflineStudents();
        if (students.length === 0) return;
        // You can add a UI indicator here if desired
        console.log(`[Offline] ${students.length} pending students to sync.`);
    }
    showPendingBadge();

})();
