/* Progressive enhancements for the public showcase; no game state is read or changed. */
(() => {
  'use strict';

  const root = document.documentElement;
  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
  const desktopPointer = matchMedia('(min-width: 960px) and (hover: hover) and (pointer: fine)');
  const connection = navigator.connection;
  const motionButton = document.getElementById('motion-toggle');
  const motionListeners = [];
  let motionPreference = null;
  let motion = false;
  try { motionPreference = localStorage.getItem('terra-showcase-motion'); } catch (_) { /* Optional preference. */ }

  function listenToMedia(query, listener) {
    if (query.addEventListener) query.addEventListener('change', listener);
    else if (query.addListener) query.addListener(listener);
  }

  function applyMotion() {
    const constrained = reducedMotion.matches || Boolean(connection?.saveData);
    motion = !constrained && motionPreference !== 'off';
    root.dataset.motion = motion ? 'on' : 'off';
    root.dataset.pageHidden = String(document.hidden);
    if (motionButton) {
      motionButton.textContent = `Анимация: ${motion ? 'вкл.' : 'выкл.'}`;
      motionButton.setAttribute('aria-pressed', String(motion));
      motionButton.setAttribute('aria-disabled', String(constrained));
      motionButton.title = constrained
        ? 'Анимация выключена настройкой уменьшения движения или экономии трафика на устройстве'
        : 'Включить или выключить атмосферные анимации';
    }
    motionListeners.forEach(listener => listener());
  }

  motionButton?.addEventListener('click', () => {
    if (reducedMotion.matches || connection?.saveData) return;
    motionPreference = motion ? 'off' : 'on';
    try { localStorage.setItem('terra-showcase-motion', motionPreference); } catch (_) { /* Still works without storage. */ }
    applyMotion();
  });
  listenToMedia(reducedMotion, applyMotion);
  connection?.addEventListener?.('change', applyMotion);
  document.addEventListener('visibilitychange', applyMotion);
  applyMotion();
  if (motionButton) motionButton.hidden = false;

  function setupNavigation() {
    const nav = document.getElementById('site-nav');
    const toggle = document.querySelector('[data-menu-toggle]');
    const menu = document.querySelector('[data-menu]');
    if (!nav) return;
    let pending = false;
    const update = () => {
      pending = false;
      nav.classList.toggle('is-scrolled', scrollY > 24);
    };
    addEventListener('scroll', () => {
      if (!pending) {
        pending = true;
        requestAnimationFrame(update);
      }
    }, { passive: true });
    update();
    if (!toggle || !menu) return;
    const closeMenu = () => {
      nav.classList.remove('menu-open');
      toggle.setAttribute('aria-expanded', 'false');
      toggle.setAttribute('aria-label', 'Открыть меню');
    };
    toggle.addEventListener('click', () => {
      const open = nav.classList.toggle('menu-open');
      toggle.setAttribute('aria-expanded', String(open));
      toggle.setAttribute('aria-label', open ? 'Закрыть меню' : 'Открыть меню');
    });
    menu.addEventListener('click', event => {
      if (event.target.closest('a')) closeMenu();
    });
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && nav.classList.contains('menu-open')) {
        closeMenu();
        toggle.focus({ preventScroll: true });
      }
    });
    document.addEventListener('pointerdown', event => {
      if (!nav.contains(event.target)) closeMenu();
    });
    listenToMedia(matchMedia('(min-width: 960px)'), closeMenu);
    toggle.hidden = false;
    root.classList.add('js');
  }

  function setupParallax() {
    const hero = document.getElementById('hero');
    if (!hero) return;
    let frame = 0;
    let x = 0;
    let y = 0;
    const allowed = () => motion && desktopPointer.matches && !document.hidden;
    const reset = () => {
      if (frame) cancelAnimationFrame(frame);
      frame = 0;
      x = y = 0;
      hero.style.setProperty('--look-x', '0px');
      hero.style.setProperty('--look-y', '0px');
    };
    hero.addEventListener('pointermove', event => {
      if (!allowed()) return;
      const rect = hero.getBoundingClientRect();
      x = ((event.clientX - rect.left) / rect.width - 0.5) * 12;
      y = ((event.clientY - rect.top) / rect.height - 0.5) * 8;
      if (!frame) frame = requestAnimationFrame(() => {
        frame = 0;
        if (!allowed()) return;
        hero.style.setProperty('--look-x', `${x.toFixed(2)}px`);
        hero.style.setProperty('--look-y', `${y.toFixed(2)}px`);
      });
    }, { passive: true });
    hero.addEventListener('pointerleave', reset);
    motionListeners.push(reset);
    listenToMedia(desktopPointer, reset);
  }

  function setupReveals() {
    const elements = [...document.querySelectorAll('[data-reveal]')];
    if (!('IntersectionObserver' in window) || !elements.length) return;
    let observer;
    const revealAll = () => {
      observer?.disconnect();
      elements.forEach(element => {
        element.classList.remove('reveal-enabled');
        element.classList.add('is-visible');
      });
    };
    if (!motion) { revealAll(); return; }
    observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('is-visible');
        observer.unobserve(entry.target);
      });
    }, { rootMargin: '0px 0px -30px 0px', threshold: 0.08 });
    elements.forEach(element => {
      // Never hide content the visitor can already see when this deferred script runs.
      if (element.getBoundingClientRect().top < innerHeight) element.classList.add('is-visible');
      else {
        element.classList.add('reveal-enabled');
        observer.observe(element);
      }
    });
    motionListeners.push(() => { if (!motion) revealAll(); });
  }

  function setupScenes() {
    const tablist = document.querySelector('.scene-tabs');
    const tabs = [...document.querySelectorAll('.scene-tab[data-scene]')];
    const entries = tabs.map(tab => ({ tab, panel: document.getElementById(`scene-${tab.dataset.scene}`) }));
    if (!tablist || !entries.length || entries.some(entry => !entry.panel)) return;
    const activate = index => entries.forEach(({ tab, panel }, position) => {
      const selected = position === index;
      tab.setAttribute('aria-selected', String(selected));
      tab.tabIndex = selected ? 0 : -1;
      panel.hidden = !selected;
    });
    entries.forEach(({ tab }, index) => {
      tab.addEventListener('click', () => activate(index));
      tab.addEventListener('keydown', event => {
        let next = index;
        if (event.key === 'ArrowRight') next = (index + 1) % entries.length;
        else if (event.key === 'ArrowLeft') next = (index - 1 + entries.length) % entries.length;
        else if (event.key === 'Home') next = 0;
        else if (event.key === 'End') next = entries.length - 1;
        else return;
        event.preventDefault();
        activate(next);
        entries[next].tab.focus();
      });
    });
    tablist.setAttribute('role', 'tablist');
    entries.forEach(({ tab, panel }) => {
      tab.setAttribute('role', 'tab');
      tab.setAttribute('aria-controls', panel.id);
      panel.setAttribute('role', 'tabpanel');
      panel.setAttribute('aria-labelledby', tab.id);
      panel.tabIndex = 0;
    });
    activate(0);
    tablist.hidden = false;
  }

  function setupSequence() {
    const track = document.querySelector('.dossier-track[data-sequence]');
    const canvas = document.getElementById('moloh-canvas');
    const visual = track?.querySelector('.dossier-visual');
    if (!track || !canvas || !visual || !('IntersectionObserver' in window)) return;
    const context = canvas.getContext('2d');
    if (!context) return;
    const count = Number(track.dataset.frames) || 24;
    const columns = Number(track.dataset.columns) || 6;
    const width = 512;
    const height = 640;
    let atlas;
    let ready = false;
    let failed = false;
    let near = false;
    let frame = 0;
    const allowed = () => motion && !reducedMotion.matches && !connection?.saveData && desktopPointer.matches && !document.hidden;
    const inView = () => {
      const bounds = track.getBoundingClientRect();
      return bounds.top < innerHeight && bounds.bottom > 0;
    };
    const stop = () => {
      if (frame) cancelAnimationFrame(frame);
      frame = 0;
      visual.classList.remove('ready');
    };
    const draw = () => {
      frame = 0;
      if (!allowed() || !ready || !inView()) return;
      const rect = track.getBoundingClientRect();
      const distance = Math.max(1, rect.height - visual.getBoundingClientRect().height);
      const progress = Math.max(0, Math.min(1, (96 - rect.top) / distance));
      const position = progress * (count - 1);
      const first = Math.floor(position);
      const second = Math.min(first + 1, count - 1);
      const mix = position - first;
      try {
        context.clearRect(0, 0, width, height);
        context.globalCompositeOperation = 'source-over';
        context.globalAlpha = 1 - mix;
        context.drawImage(atlas, first % columns * width, Math.floor(first / columns) * height,
          width, height, 0, 0, width, height);
        if (mix > 0) {
          context.globalCompositeOperation = 'lighter';
          context.globalAlpha = mix;
          context.drawImage(atlas, second % columns * width, Math.floor(second / columns) * height,
            width, height, 0, 0, width, height);
        }
        visual.classList.add('ready');
      } catch (_) {
        failed = true;
        ready = false;
        stop();
      } finally {
        context.globalAlpha = 1;
        context.globalCompositeOperation = 'source-over';
      }
    };
    const schedule = () => {
      if (allowed() && ready && near && inView() && !frame) frame = requestAnimationFrame(draw);
    };
    const sync = () => {
      if (!allowed() || !near || failed) { stop(); return; }
      if (!atlas) {
        atlas = new Image();
        atlas.decoding = 'async';
        atlas.onload = () => {
          ready = atlas.naturalWidth >= columns * width && atlas.naturalHeight >= Math.ceil(count / columns) * height;
          failed = !ready;
          schedule();
        };
        atlas.onerror = () => { failed = true; stop(); };
        atlas.src = track.dataset.sequence;
      } else schedule();
    };
    new IntersectionObserver(entries => {
      near = entries[0].isIntersecting;
      sync();
    }, { rootMargin: '300px 0px' }).observe(track);
    addEventListener('scroll', schedule, { passive: true });
    addEventListener('resize', sync, { passive: true });
    motionListeners.push(sync);
    listenToMedia(desktopPointer, sync);
  }

  const plainClick = event => event.button === 0 && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey;

  function bindDialog(dialog, closeSelector, onClose) {
    dialog.querySelectorAll(closeSelector).forEach(button => button.addEventListener('click', () => dialog.close()));
    dialog.addEventListener('click', event => {
      if (event.target !== dialog) return;
      const rect = dialog.getBoundingClientRect();
      if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close();
    });
    dialog.addEventListener('close', onClose);
  }

  function setupGallery() {
    const links = [...document.querySelectorAll('a[data-gallery]')];
    const dialog = document.getElementById('gallery-dialog');
    const image = document.getElementById('gallery-image');
    const caption = document.getElementById('gallery-caption');
    if (!links.length || !dialog?.showModal || !image || !caption) return;
    let current = 0;
    let opener;
    const show = index => {
      current = (index + links.length) % links.length;
      const link = links[current];
      const label = link.dataset.caption || link.querySelector('img')?.alt || 'Кадр из игры';
      image.src = link.href;
      image.alt = label;
      caption.textContent = `${current + 1} / ${links.length} — ${label}`;
    };
    links.forEach((link, index) => link.addEventListener('click', event => {
      if (!plainClick(event)) return;
      event.preventDefault();
      opener = link;
      show(index);
      if (!dialog.open) dialog.showModal();
    }));
    dialog.querySelector('[data-gallery-prev]')?.addEventListener('click', () => show(current - 1));
    dialog.querySelector('[data-gallery-next]')?.addEventListener('click', () => show(current + 1));
    dialog.addEventListener('keydown', event => {
      if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
      event.preventDefault();
      show(current + (event.key === 'ArrowRight' ? 1 : -1));
    });
    bindDialog(dialog, '[data-gallery-close]', () => opener?.focus({ preventScroll: true }));
  }

  function setupTrailer() {
    const dialog = document.getElementById('trailer-dialog');
    const video = document.getElementById('trailer-video');
    const caption = document.getElementById('trailer-caption');
    if (!dialog?.showModal || !video) return;
    let opener;
    document.querySelectorAll('a[data-trailer-open]').forEach(link => link.addEventListener('click', event => {
      if (!plainClick(event)) return;
      event.preventDefault();
      opener = link;
      video.poster = link.dataset.poster || '';
      video.src = link.href;
      if (caption) caption.textContent = link.dataset.title || 'Трейлер «Терры»';
      if (!dialog.open) dialog.showModal();
      // Opening the player is explicit; playback remains under the visitor's control.
      video.load();
    }));
    bindDialog(dialog, '[data-trailer-close]', () => {
      video.pause();
      video.removeAttribute('src');
      video.removeAttribute('poster');
      video.load();
      opener?.focus({ preventScroll: true });
    });
  }

  async function updateRelease() {
    if (!('fetch' in window) || !('AbortController' in window)) return;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 3000);
    const repository = '/89244114832maxim-ai/terra-play/';
    const officialLink = value => {
      try {
        const url = new URL(value);
        return url.origin === 'https://github.com' && !url.username && !url.password &&
          url.pathname.startsWith(`${repository}releases/`) ? url.href : null;
      } catch (_) { return null; }
    };
    const setText = (id, value) => {
      const element = document.getElementById(id);
      if (element && value) element.textContent = value;
    };
    try {
      const response = await fetch('https://api.github.com/repos/89244114832maxim-ai/terra-play/releases/latest', {
        signal: controller.signal,
        credentials: 'omit',
        headers: { Accept: 'application/vnd.github+json' }
      });
      if (!response.ok) return;
      const release = await response.json();
      if (release.draft || !officialLink(release.html_url)) return;
      if (typeof release.tag_name === 'string') setText('release-version', release.tag_name.slice(0, 80));
      const date = new Date(release.published_at);
      if (Number.isFinite(date.getTime())) {
        setText('release-date', date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' }));
      }
      const archive = Array.isArray(release.assets) && release.assets.find(asset =>
        typeof asset.name === 'string' && /\.zip$/i.test(asset.name) && officialLink(asset.browser_download_url));
      const download = document.getElementById('release-download');
      if (download) download.href = archive ? officialLink(archive.browser_download_url) : officialLink(release.html_url);
      if (archive && Number.isFinite(archive.size) && archive.size > 0) {
        setText('release-size', `ZIP · ${(archive.size / 1e6).toLocaleString('ru-RU', { maximumFractionDigits: 1 })} МБ`);
      }
      if (typeof release.name === 'string' && release.name.trim() && release.name !== release.tag_name) {
        setText('release-note', release.name.trim().slice(0, 140));
      }
    } catch (_) { /* GitHub can be offline or rate-limited; the static release link remains available. */ }
    finally { clearTimeout(timeout); }
  }

  setupNavigation();
  setupParallax();
  setupReveals();
  setupScenes();
  setupSequence();
  setupGallery();
  setupTrailer();
  updateRelease();
})();
