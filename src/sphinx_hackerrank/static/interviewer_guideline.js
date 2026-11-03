(() => {
  const copyText = async (text) => {
    if (navigator.clipboard?.writeText) {
      try {
        await navigator.clipboard.writeText(text);
        return;
      } catch {
        // Try selection-based copying when clipboard access is denied.
      }
    }

    const focus = document.activeElement;
    const selection = document.getSelection();
    const ranges = selection
      ? Array.from({ length: selection.rangeCount }, (_, index) =>
          selection.getRangeAt(index).cloneRange(),
        )
      : [];
    const buffer = document.createElement("textarea");
    buffer.value = text;
    buffer.readOnly = true;
    buffer.style.cssText = "position:fixed;left:-9999px;top:0";
    document.body.append(buffer);
    buffer.select();
    try {
      if (!document.execCommand("copy")) {
        throw new Error("Copy was not permitted");
      }
    } finally {
      buffer.remove();
      if (focus instanceof HTMLElement) {
        focus.focus({ preventScroll: true });
      }
      if (selection) {
        selection.removeAllRanges();
        ranges.forEach((range) => selection.addRange(range));
      }
    }
  };

  const enhance = () => {
    document.querySelectorAll(".hr-interviewer-guideline pre").forEach((pre) => {
      if (pre.closest(".hr-code-block, .linenos")) {
        return;
      }
      const wrapper = document.createElement("div");
      wrapper.className = "hr-code-block";
      const controls = document.createElement("div");
      controls.className = "hr-copy-controls";
      const status = document.createElement("span");
      status.className = "hr-copy-status";
      status.setAttribute("role", "status");
      const button = document.createElement("button");
      button.type = "button";
      button.className = "hr-copy-code";
      button.textContent = "Copy code";
      let resetTimer;
      button.addEventListener("click", async () => {
        if (button.getAttribute("aria-busy") === "true") {
          return;
        }
        clearTimeout(resetTimer);
        button.setAttribute("aria-busy", "true");
        status.textContent = "Copying...";
        try {
          const code = pre.cloneNode(true);
          code.querySelectorAll(".linenos").forEach((node) => node.remove());
          await copyText(code.textContent);
          status.textContent = "Copied";
          resetTimer = setTimeout(() => {
            status.textContent = "";
          }, 2000);
        } catch {
          status.textContent = "Copy failed. Select and copy the code manually.";
        } finally {
          button.removeAttribute("aria-busy");
        }
      });
      controls.append(status, button);
      pre.before(wrapper);
      wrapper.append(controls, pre);
    });
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", enhance, { once: true });
  } else {
    enhance();
  }
})();
