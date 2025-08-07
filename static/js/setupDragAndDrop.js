


document.addEventListener("DOMContentLoaded", () => {
  const uploadZone = document.getElementById("upload-zone");
  const fileInput = document.getElementById("las-file");

  if (uploadZone && fileInput) {
    const preventDefaults = (e) => {
      e.preventDefault();
      e.stopPropagation();
    };

    const handleDrop = (e) => {
      preventDefaults(e);
      const dt = e.dataTransfer;
      const files = dt.files;

      if (files.length) {
        fileInput.files = files;

        const event = new Event("change", { bubbles: true });
        fileInput.dispatchEvent(event);
      }
    };

    ["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
      uploadZone.addEventListener(eventName, preventDefaults, false);
    });

    ["dragenter", "dragover"].forEach((eventName) => {
      uploadZone.addEventListener(
        eventName,
        () => uploadZone.classList.add("dragover"),
        false
      );
    });

    ["dragleave", "drop"].forEach((eventName) => {
      uploadZone.addEventListener(
        eventName,
        () => uploadZone.classList.remove("dragover"),
        false
      );
    });

    uploadZone.addEventListener("drop", handleDrop, false);

    // uploadZone.addEventListener("click", () => fileInput.click());
  }

  const scrollTopBtn = document.getElementById("scroll-top");

  if (scrollTopBtn) {
    window.addEventListener("scroll", () => {
      if (window.pageYOffset > 300) {
        scrollTopBtn.classList.remove("d-none");
      } else {
        scrollTopBtn.classList.add("d-none");
      }
    });

    scrollTopBtn.addEventListener("click", () => {
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }
});
