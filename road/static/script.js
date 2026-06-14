document.addEventListener("DOMContentLoaded", () => {

    // IMAGE PREVIEW
    const imageInput = document.getElementById("imageInput");
    const previewImg = document.getElementById("previewImg");
    const previewArea = document.getElementById("previewArea");
    const spinner = document.getElementById("spinner");
    const uploadForm = document.getElementById("uploadForm");
    const submitBtn = document.getElementById("submitBtn");

    if (imageInput) {
        imageInput.addEventListener("change", () => {
            const file = imageInput.files[0];
            if (!file) return;

            previewImg.src = URL.createObjectURL(file);
            previewArea.classList.remove("hidden");
        });
    }

    if (uploadForm) {
        uploadForm.addEventListener("submit", () => {
            spinner.classList.remove("hidden");
            submitBtn.disabled = true;
            submitBtn.innerText = "Processing...";
        });
    }

    // OVERLAY OPACITY
    const blendSlider = document.getElementById("blendSlider");
    const overlayImg = document.getElementById("overlayImg");

    if (blendSlider && overlayImg) {
        blendSlider.addEventListener("input", () => {
            overlayImg.style.opacity = blendSlider.value / 100;
        });
    }

    // ADVANCED SECTION TOGGLE
    const toggleBtn = document.getElementById("toggleAdvanced");
    const advancedSection = document.getElementById("advancedSection");

    if (toggleBtn && advancedSection) {
        toggleBtn.addEventListener("click", () => {
            advancedSection.classList.toggle("hidden");
            toggleBtn.innerText = advancedSection.classList.contains("hidden")
                ? "Show Advanced Output"
                : "Hide Advanced Output";
        });
    }

});
