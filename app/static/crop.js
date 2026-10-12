(() => {
  function clamp(value, minimum, maximum) {
    return Math.min(Math.max(value, minimum), maximum);
  }

  function normalizeRect(rect, bounds) {
    if (bounds.width <= 0 || bounds.height <= 0) {
      throw new RangeError("Video bounds must have positive dimensions.");
    }
    return {
      x: (rect.left - bounds.left) / bounds.width,
      y: (rect.top - bounds.top) / bounds.height,
      width: rect.width / bounds.width,
      height: rect.height / bounds.height,
    };
  }

  function moveRect(rect, dx, dy, bounds) {
    return {
      ...rect,
      left: clamp(rect.left + dx, bounds.left, bounds.left + bounds.width - rect.width),
      top: clamp(rect.top + dy, bounds.top, bounds.top + bounds.height - rect.height),
    };
  }

  function resizeRect(rect, handle, dx, dy, bounds, minWidth, minHeight) {
    if (!["nw", "ne", "sw", "se"].includes(handle)) {
      throw new RangeError("Crop handle must be a corner.");
    }
    const minimumWidth = Math.min(minWidth, bounds.width);
    const minimumHeight = Math.min(minHeight, bounds.height);
    const leftEdge = rect.left;
    const rightEdge = rect.left + rect.width;
    const topEdge = rect.top;
    const bottomEdge = rect.top + rect.height;

    const left = handle.includes("w")
      ? clamp(leftEdge + dx, bounds.left, rightEdge - minimumWidth)
      : leftEdge;
    const right = handle.includes("e")
      ? clamp(rightEdge + dx, left + minimumWidth, bounds.left + bounds.width)
      : rightEdge;
    const top = handle.includes("n")
      ? clamp(topEdge + dy, bounds.top, bottomEdge - minimumHeight)
      : topEdge;
    const bottom = handle.includes("s")
      ? clamp(bottomEdge + dy, top + minimumHeight, bounds.top + bounds.height)
      : bottomEdge;

    return { left, top, width: right - left, height: bottom - top };
  }

  function createCropOverlay({ frame, video, toggle, reset }) {
    const overlay = frame.querySelector("[data-crop-overlay]");
    const box = overlay.querySelector("[data-crop-box]");
    let enabled = false;
    let region = null;
    let drag = null;

    function videoBounds() {
      const bounds = video.getBoundingClientRect();
      return {
        left: bounds.left,
        top: bounds.top,
        width: bounds.width,
        height: bounds.height,
      };
    }

    function pixelRect(bounds) {
      return {
        left: bounds.left + region.x * bounds.width,
        top: bounds.top + region.y * bounds.height,
        width: region.width * bounds.width,
        height: region.height * bounds.height,
      };
    }

    function render() {
      const bounds = videoBounds();
      const frameBounds = frame.getBoundingClientRect();
      overlay.style.left = `${bounds.left - frameBounds.left}px`;
      overlay.style.top = `${bounds.top - frameBounds.top}px`;
      overlay.style.width = `${bounds.width}px`;
      overlay.style.height = `${bounds.height}px`;
      overlay.hidden = !enabled || !region || bounds.width <= 0 || bounds.height <= 0;
      toggle.textContent = enabled ? "关闭裁切" : "启用裁切";
      toggle.setAttribute("aria-pressed", String(enabled));
      reset.disabled = !enabled;
      if (overlay.hidden) return;
      box.style.left = `${region.x * 100}%`;
      box.style.top = `${region.y * 100}%`;
      box.style.width = `${region.width * 100}%`;
      box.style.height = `${region.height * 100}%`;
    }

    function setEnabled(value) {
      enabled = Boolean(value);
      region = enabled ? (region || { x: 0, y: 0, width: 1, height: 1 }) : null;
      render();
    }

    function startDrag(event) {
      if (!enabled || !region || video.videoWidth <= 0 || video.videoHeight <= 0) return;
      const handle = event.target.closest?.("[data-handle]")?.dataset.handle;
      const bounds = videoBounds();
      const rect = pixelRect(bounds);
      const minWidth = Math.min(bounds.width, bounds.width * 16 / video.videoWidth);
      const minHeight = Math.min(bounds.height, bounds.height * 16 / video.videoHeight);
      event.preventDefault();
      box.setPointerCapture?.(event.pointerId);
      drag = {
        handle: handle || null,
        bounds,
        rect,
        minWidth,
        minHeight,
        startX: event.clientX,
        startY: event.clientY,
      };
    }

    function moveDrag(event) {
      if (!drag) return;
      const dx = event.clientX - drag.startX;
      const dy = event.clientY - drag.startY;
      const rect = drag.handle
        ? resizeRect(
          drag.rect,
          drag.handle,
          dx,
          dy,
          drag.bounds,
          drag.minWidth,
          drag.minHeight,
        )
        : moveRect(drag.rect, dx, dy, drag.bounds);
      region = normalizeRect(rect, drag.bounds);
      render();
    }

    function endDrag(event) {
      if (!drag) return;
      box.releasePointerCapture?.(event.pointerId);
      drag = null;
    }

    toggle.addEventListener("click", () => setEnabled(!enabled));
    reset.addEventListener("click", () => {
      region = { x: 0, y: 0, width: 1, height: 1 };
      setEnabled(true);
    });
    box.addEventListener("pointerdown", startDrag);
    box.addEventListener("pointermove", moveDrag);
    box.addEventListener("pointerup", endDrag);
    box.addEventListener("pointercancel", endDrag);
    video.addEventListener("loadedmetadata", render);
    video.addEventListener("resize", render);
    window.addEventListener?.("resize", render);
    render();

    return {
      setEnabled,
      reset() {
        region = { x: 0, y: 0, width: 1, height: 1 };
        setEnabled(true);
      },
      region() {
        return enabled ? region : null;
      },
    };
  }

  window.ClipGifCrop = { createCropOverlay, moveRect, normalizeRect, resizeRect };
})();
