        let currentMangaId = null;
        let currentMangaData = null;

        // Reader State
        let isPagedMode = false;
        let currentImages = [];
        let currentPageIndex = 0;

        const loader = document.getElementById('loader');
        const views = {
            home: document.getElementById('home-view'),
            detail: document.getElementById('detail-view'),
            reader: document.getElementById('reader-view')
        };

        function showLoader() { loader.style.display = 'block'; }
        function hideLoader() { loader.style.display = 'none'; }

        function navigate(viewName) {
            Object.values(views).forEach(v => v.classList.remove('active'));
            views[viewName].classList.add('active');
            window.scrollTo(0, 0);
        }

        async function performSearch() {
            const query = document.getElementById('search-input').value.trim();
            if (!query) return;

            navigate('home');
            showLoader();
            document.getElementById('manga-grid').innerHTML = '';
            document.getElementById('home-title').innerText = `Search Results for "${query}"`;

            try {
                const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
                const data = await res.json();

                const grid = document.getElementById('manga-grid');
                if (data.length === 0) {
                    grid.innerHTML = '<p>No results found.</p>';
                } else {
                    data.forEach(manga => {
                        const card = document.createElement('div');
                        card.className = 'manga-card';

                        const proxyCover = manga.cover_url ? `/api/proxy-image?url=${encodeURIComponent(manga.cover_url)}` : 'https://via.placeholder.com/200x300?text=No+Cover';

                        card.innerHTML = `
                            <img loading="lazy">
                            <div class="info">
                                <h3></h3>
                            </div>
                        `;
                        card.querySelector('img').src = proxyCover;
                        card.querySelector('img').alt = manga.title;
                        card.querySelector('h3').textContent = manga.title;
                        card.onclick = () => loadMangaDetail(manga.id);
                        grid.appendChild(card);
                    });
                }
            } catch (e) {
                console.error(e);
                alert("Search failed. Check console.");
            } finally {
                hideLoader();
            }
        }

        async function loadMangaDetail(mangaId, force = false) {
            navigate('detail');
            showLoader();
            const chapContainer = document.getElementById('chapters-container');
            chapContainer.innerHTML = '';
            document.getElementById('detail-title').innerText = 'Loading...';
            document.getElementById('detail-synopsis').innerText = '';
            document.getElementById('detail-cover').src = '';
            document.getElementById('btn-read-first').style.display = 'none';

            currentMangaId = mangaId;

            try {
                const url = `/api/manga/${mangaId}${force ? '?force=true' : ''}`;
                const res = await fetch(url);
                if (!res.ok) throw new Error("Manga not found or error fetching details");
                const data = await res.json();
                currentMangaData = data;

                document.getElementById('detail-title').innerText = data.title;
                document.getElementById('detail-synopsis').innerText = data.synopsis || "No synopsis available.";

                const proxyCover = data.cover_url ? `/api/proxy-image?url=${encodeURIComponent(data.cover_url)}` : 'https://via.placeholder.com/250x350?text=No+Cover';
                document.getElementById('detail-cover').src = proxyCover;

                document.getElementById('chapter-count').innerText = `(${data.chapters.length})`;

                if (data.chapters.length > 0) {
                    const bookmark = getBookmark(mangaId);

                    // aquareader usually lists latest first. We display as returned.
                    data.chapters.forEach(chap => {
                        const div = document.createElement('div');
                        div.className = 'chapter-item';

                        const chapSlug = chap.id.split('/').pop();

                        const linkSpan = document.createElement('span');
                        linkSpan.className = 'chapter-link';

                        // Highlight bookmark
                        if (bookmark && bookmark.chapterSlug === chapSlug) {
                            linkSpan.innerHTML = `<span style="color: var(--accent-secondary);">★</span> ${chap.title}`;
                        } else {
                            linkSpan.textContent = chap.title;
                        }

                        linkSpan.onclick = () => loadChapter(chapSlug, chap.title);

                        const dlBtn = document.createElement('button');
                        dlBtn.className = 'btn-download';
                        dlBtn.title = 'Download CBZ';
                        dlBtn.textContent = '↓ CBZ';
                        dlBtn.onclick = () => startDownload(mangaId, chapSlug, dlBtn);

                        div.appendChild(linkSpan);
                        div.appendChild(dlBtn);
                        chapContainer.appendChild(div);
                    });

                    const btnRead = document.getElementById('btn-read-first');

                    if (bookmark) {
                        btnRead.textContent = 'Resume Reading';
                        btnRead.onclick = () => loadChapter(bookmark.chapterSlug, bookmark.chapterTitle);
                    } else {
                        // The "first" chapter is usually at the end of the array if sorted newest-first
                        const firstChap = data.chapters[data.chapters.length - 1];
                        const firstChapSlug = firstChap.id.split('/').pop();
                        btnRead.textContent = 'Read First Chapter';
                        btnRead.onclick = () => loadChapter(firstChapSlug, firstChap.title);
                    }
                    btnRead.style.display = 'inline-block';
                } else {
                    chapContainer.innerHTML = '<p>No chapters found.</p>';
                }

                document.getElementById('btn-force-update').onclick = () => loadMangaDetail(mangaId, true);

            } catch (e) {
                console.error(e);
                document.getElementById('detail-title').innerText = "Error loading details.";
                chapContainer.innerHTML = `<p style="color:red;">Error: Could not load manga details. ${e.message}</p>`;
            } finally {
                hideLoader();
            }
        }

        function backToDetail() {
            if (currentMangaId) {
                navigate('detail');
            } else {
                navigate('home');
            }
        }

        function saveBookmark(mangaId, chapterSlug, chapterTitle) {
            const history = JSON.parse(localStorage.getItem('mangaHistory') || '{}');
            history[mangaId] = { chapterSlug, chapterTitle, timestamp: Date.now() };
            localStorage.setItem('mangaHistory', JSON.stringify(history));
        }

        function getBookmark(mangaId) {
            const history = JSON.parse(localStorage.getItem('mangaHistory') || '{}');
            return history[mangaId];
        }

        async function loadChapter(chapterSlug, chapterTitle) {
            navigate('reader');
            showLoader();
            const container = document.getElementById('reader-images');
            container.innerHTML = '';
            document.getElementById('reader-title').innerText = `${currentMangaData ? currentMangaData.title : ''} - ${chapterTitle}`;

            saveBookmark(currentMangaId, chapterSlug, chapterTitle);

            try {
                const res = await fetch(`/api/chapter/${currentMangaId}/${chapterSlug}`);
                if (!res.ok) throw new Error("Chapter images not found");
                const data = await res.json();

                if (data.images.length === 0) {
                    container.innerHTML = '<p style="padding: 2rem;">No images found for this chapter.</p>';
                    currentImages = [];
                } else {
                    currentImages = data.images.map(url => `/api/proxy-image?url=${encodeURIComponent(url)}`);
                    currentPageIndex = 0;
                    renderReader();
                }
            } catch (e) {
                console.error(e);
                container.innerHTML = '<p style="color: red; padding: 2rem;">Error loading chapter images. The source site might be blocking the request.</p>';
            } finally {
                hideLoader();
            }
        }

        function toggleReaderMode() {
            const toggle = document.getElementById('reader-mode-toggle');
            isPagedMode = toggle.checked;

            // Save preference
            localStorage.setItem('readerMode', isPagedMode ? 'paged' : 'webtoon');

            renderReader();
        }

        function renderReader() {
            const container = document.getElementById('reader-images');
            const topNav = document.getElementById('paged-reader-nav');
            const bottomNav = document.getElementById('paged-reader-nav-bottom');
            const progress = document.getElementById('reader-progress');
            container.innerHTML = '';

            if (currentImages.length === 0) return;

            if (isPagedMode) {
                topNav.style.display = 'flex';
                bottomNav.style.display = 'flex';
                progress.innerText = `Page ${currentPageIndex + 1} of ${currentImages.length}`;

                const img = document.createElement('img');
                img.src = currentImages[currentPageIndex];
                img.alt = `Page ${currentPageIndex + 1}`;

                img.onerror = function() {
                    console.error(`Failed to load image at index ${currentPageIndex}`);
                    this.style.display = 'none';
                    const err = document.createElement('div');
                    err.style.color = 'red';
                    err.style.padding = '1rem';
                    err.innerText = `Failed to load image ${currentPageIndex+1}`;
                    this.parentNode.insertBefore(err, this);
                };

                container.appendChild(img);

                // Preload next image
                if (currentPageIndex < currentImages.length - 1) {
                    const preload = new Image();
                    preload.src = currentImages[currentPageIndex + 1];
                }

                // Scroll to top of image gently
                window.scrollTo({ top: 0, behavior: 'smooth' });

            } else {
                topNav.style.display = 'none';
                bottomNav.style.display = 'none';
                progress.innerText = `${currentImages.length} Pages`;

                currentImages.forEach((src, idx) => {
                    const img = document.createElement('img');
                    img.src = src;
                    img.alt = `Page ${idx + 1}`;
                    img.loading = "lazy";

                    img.onerror = function() {
                        this.style.display = 'none';
                        const err = document.createElement('div');
                        err.style.color = 'red';
                        err.style.padding = '1rem';
                        err.innerText = `Failed to load image ${idx+1}`;
                        this.parentNode.insertBefore(err, this);
                    };

                    container.appendChild(img);
                });
            }
        }

        function prevPage() {
            if (currentPageIndex > 0) {
                currentPageIndex--;
                renderReader();
            }
        }

        function nextPage() {
            if (currentPageIndex < currentImages.length - 1) {
                currentPageIndex++;
                renderReader();
            }
        }

        async function startDownload(mangaId, chapSlug, btnElement) {
            btnElement.disabled = true;
            btnElement.textContent = 'Starting...';

            try {
                const res = await fetch(`/api/download/${mangaId}/${chapSlug}`);
                const data = await res.json();

                if (data.job_id) {
                    pollDownloadJob(data.job_id, btnElement);
                } else {
                    btnElement.textContent = 'Error';
                    btnElement.disabled = false;
                }
            } catch (e) {
                console.error(e);
                btnElement.textContent = 'Error';
                btnElement.disabled = false;
            }
        }

        async function pollDownloadJob(jobId, btnElement) {
            const interval = setInterval(async () => {
                try {
                    const res = await fetch(`/api/download/status/${jobId}`);

                    // Since it could be a zip payload, we should check Content-Type
                    // before trying to parse JSON.
                    const contentType = res.headers.get('content-type') || '';
                    if (contentType.includes('application/zip') || contentType.includes('application/octet-stream')) {
                        clearInterval(interval);
                        btnElement.textContent = 'Done!';
                        btnElement.disabled = false;

                        // Trigger file download
                        const blob = await res.blob();
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');

                        // Extract filename from disposition if possible, else fallback
                        const disposition = res.headers.get('content-disposition');
                        let filename = 'download.cbz';
                        if (disposition && disposition.indexOf('attachment') !== -1) {
                            const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
                            const matches = filenameRegex.exec(disposition);
                            if (matches != null && matches[1]) {
                                filename = matches[1].replace(/['"]/g, '');
                            }
                        }

                        a.href = url;
                        a.download = filename;
                        document.body.appendChild(a);
                        a.click();
                        a.remove();
                        window.URL.revokeObjectURL(url);
                        return;
                    }

                    const data = await res.json();
                    if (data.status === 'pending' || data.status === 'completed') {
                        btnElement.textContent = `${data.progress}%`;
                    } else if (data.status === 'error') {
                        clearInterval(interval);
                        btnElement.textContent = 'Error';
                        btnElement.disabled = false;
                    }
                } catch (e) {
                    clearInterval(interval);
                    btnElement.textContent = 'Error';
                    btnElement.disabled = false;
                }
            }, 1000);
        }

        // Keyboard navigation for paged mode
        document.addEventListener('keydown', (e) => {
            if (views.reader.classList.contains('active') && isPagedMode) {
                if (e.key === 'ArrowLeft') prevPage();
                if (e.key === 'ArrowRight') nextPage();
            }
        });

        // Only search if user typed something, don't auto-search which could hit limits
        window.onload = () => {
            // Load saved reader mode
            const savedMode = localStorage.getItem('readerMode');
            if (savedMode === 'paged') {
                document.getElementById('reader-mode-toggle').checked = true;
                isPagedMode = true;
            }

            document.getElementById('search-input').value = 'solo leveling';
            performSearch();
        };
