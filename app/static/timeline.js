(() => {
  const GAP = 0.1;
  const MAX_CLIP = 60;

  function formatTime(seconds) {
    const value = Math.max(0, Number(seconds) || 0);
    const tenths = Math.round(value * 10);
    const minutes = Math.floor(tenths / 600);
    const remainder = tenths % 600;
    const wholeSeconds = Math.floor(remainder / 10);
    const fraction = remainder % 10;
    return `${String(minutes).padStart(2, "0")}:${String(wholeSeconds).padStart(2, "0")}.${fraction}`;
  }

  function createTimeline(elements, video) {
    const { startRange, endRange, selectionText, selectionFill, midTime, endTime } = elements;
    let duration = 0;

    function values() {
      return { start: Number(startRange.value), end: Number(endRange.value) };
    }

    function update(changed) {
      let start = Number(startRange.value);
      let end = Number(endRange.value);
      const maximumLength = Math.min(MAX_CLIP, duration);
      if (changed === "start") {
        start = Math.min(start, duration - GAP);
        if (end - start > maximumLength) start = end - maximumLength;
        if (end - start < GAP) start = end - GAP;
      } else {
        end = Math.max(end, GAP);
        if (end - start > maximumLength) end = start + maximumLength;
        if (end - start < GAP) end = start + GAP;
      }
      start = Math.max(0, Math.min(start, duration - GAP));
      end = Math.max(start + GAP, Math.min(end, duration));
      startRange.value = start.toFixed(1);
      endRange.value = end.toFixed(1);
      selectionText.textContent = `${formatTime(start)} - ${formatTime(end)}`;

      const range = Math.max(duration, GAP);
      selectionFill.style.left = `${(start / range) * 100}%`;
      selectionFill.style.width = `${((end - start) / range) * 100}%`;
      return { start, end };
    }

    function setDuration(seconds) {
      duration = seconds;
      const maximum = Math.floor(duration * 10) / 10;
      startRange.max = maximum.toFixed(1);
      endRange.max = maximum.toFixed(1);
      startRange.min = "0";
      endRange.min = GAP.toFixed(1);
      startRange.value = "0";
      endRange.value = Math.min(3, maximum).toFixed(1);
      midTime.textContent = formatTime(duration / 2);
      endTime.textContent = formatTime(duration);
      return update("end");
    }

    startRange.addEventListener("input", () => update("start"));
    endRange.addEventListener("input", () => update("end"));
    startRange.addEventListener("change", () => update("start"));
    endRange.addEventListener("change", () => update("end"));

    return {
      setDuration,
      values,
      update,
      formatTime,
      jumpToStart() {
        video.currentTime = values().start;
      },
      jumpToEnd() {
        video.currentTime = values().end;
      },
    };
  }

  window.ClipGifTimeline = { createTimeline, formatTime };
})();
