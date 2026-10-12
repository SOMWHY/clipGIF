(() => {
  const $ = (selector) => document.querySelector(selector);
  const form = $("#previewForm");
  const loadButton = $("#loadButton");
  const generateButton = $("#generateButton");
  const urlInput = $("#videoUrl");
  const cookieInput = $("#cookieFile");
  const notice = $("#notice");
  const editor = $("#editor");
  const resultPanel = $("#resultPanel");
  const video = $("#sourceVideo");
  const timeline = window.ClipGifTimeline.createTimeline({
    startRange: $("#startRange"),
    endRange: $("#endRange"),
    selectionText: $("#selectionText"),
    selectionFill: $("#selectionFill"),
    midTime: $("#midTime"),
    endTime: $("#endTime"),
  }, video);

  let previewId = null;
  let previewLoop = false;

  function showNotice(message, isError = false) {
    notice.textContent = message;
    notice.classList.toggle("notice-error", isError);
    notice.hidden = !message;
  }

  async function readError(response) {
    let detail = "请求失败，请稍后重试。";
    try {
      const payload = await response.json();
      if (typeof payload.detail === "string") detail = payload.detail;
      else if (Array.isArray(payload.detail)) detail = payload.detail.map((item) => item.msg).join("；");
    } catch (_error) {
      detail = `请求失败（HTTP ${response.status}）。`;
    }
    return detail;
  }

  async function waitForPreview(id) {
    const labels = {
      pending: "任务排队中…",
      resolving: "正在解析视频链接…",
      downloading: "正在下载视频…",
      previewing: "正在生成浏览器预览…",
    };
    for (let attempt = 0; attempt < 1200; attempt += 1) {
      await new Promise((resolve) => window.setTimeout(resolve, 500));
      const response = await fetch(`/api/previews/${id}`);
      if (!response.ok) throw new Error(await readError(response));
      const state = await response.json();
      if (state.status === "ready") return state;
      if (state.status === "failed") throw new Error(state.error || "视频准备失败。");
      showNotice(labels[state.status] || "正在准备视频…");
    }
    throw new Error("视频准备时间过长，请稍后重试。");
  }

  async function waitForTask(id) {
    for (let attempt = 0; attempt < 1200; attempt += 1) {
      await new Promise((resolve) => window.setTimeout(resolve, 500));
      const response = await fetch(`/api/tasks/${id}`);
      if (!response.ok) throw new Error(await readError(response));
      const state = await response.json();
      if (state.status === "success") return state;
      if (state.status === "failed") throw new Error(state.error || "GIF 生成失败。");
      showNotice(state.status === "transcoding" ? "正在转码 GIF…" : "正在剪辑片段并生成调色板…");
    }
    throw new Error("GIF 生成时间过长，请稍后重试。");
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = new FormData();
    data.append("url", urlInput.value.trim());
    if (cookieInput.files[0]) data.append("cookies", cookieInput.files[0]);
    loadButton.disabled = true;
    resultPanel.hidden = true;
    editor.hidden = true;
    showNotice("正在提交视频…");
    try {
      const response = await fetch("/api/previews", { method: "POST", body: data });
      if (!response.ok) throw new Error(await readError(response));
      const created = await response.json();
      previewId = created.preview_id;
      $("#platformBadge").textContent = `已识别：${created.platform === "bilibili" ? "B站" : created.platform}`;
      $("#platformBadge").hidden = false;
      showNotice("已识别平台，开始准备预览…");
      const ready = await waitForPreview(previewId);
      if (ready.duration < 0.1) throw new Error("视频时长过短，无法选择有效片段。");
      video.src = ready.video_url;
      video.load();
      const values = timeline.setDuration(ready.duration);
      $("#durationBadge").textContent = `总时长 ${window.ClipGifTimeline.formatTime(ready.duration)}`;
      editor.hidden = false;
      resultPanel.hidden = true;
      showNotice("视频预览已就绪。可以拖动时间轴选取片段。");
      if (values.end - values.start > 60) timeline.update("end");
    } catch (error) {
      showNotice(error.message || "视频准备失败。", true);
    } finally {
      loadButton.disabled = false;
    }
  });

  $("#previewSelection").addEventListener("click", async () => {
    const { start } = timeline.values();
    previewLoop = true;
    video.currentTime = start;
    try {
      await video.play();
    } catch (_error) {
      showNotice("浏览器未能自动播放，请点击视频播放按钮。", true);
    }
  });

  video.addEventListener("timeupdate", () => {
    if (previewLoop && video.currentTime >= timeline.values().end) {
      video.currentTime = timeline.values().start;
    }
  });
  video.addEventListener("pause", () => { previewLoop = false; });
  $("#jumpStart").addEventListener("click", () => timeline.jumpToStart());
  $("#jumpEnd").addEventListener("click", () => timeline.jumpToEnd());

  generateButton.addEventListener("click", async () => {
    if (!previewId) return;
    const { start, end } = timeline.values();
    if (end <= start || end - start > 60) {
      showNotice("请选择大于 0 秒且不超过 60 秒的片段。", true);
      return;
    }
    generateButton.disabled = true;
    showNotice("正在创建 GIF 任务…");
    try {
      const response = await fetch(`/api/previews/${previewId}/gif`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ start, end }),
      });
      if (!response.ok) throw new Error(await readError(response));
      const task = await response.json();
      const result = await waitForTask(task.task_id);
      $("#gifPreview").src = `${result.gif_url}?v=${Date.now()}`;
      $("#downloadButton").href = result.download_url;
      resultPanel.hidden = false;
      showNotice("GIF 已生成，可以预览并下载。");
      resultPanel.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (error) {
      showNotice(error.message || "GIF 生成失败。", true);
    } finally {
      generateButton.disabled = false;
    }
  });

  cookieInput.addEventListener("change", () => {
    $("#cookieLabel").textContent = cookieInput.files[0]?.name || "上传 cookies.txt（可选）";
  });
})();
