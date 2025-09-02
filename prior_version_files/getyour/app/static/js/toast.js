;(function () {
    const toastElement = document.getElementById("toast")
    const toastBody = document.getElementById("toast-body")
    const toast = new bootstrap.Toast(toastElement, { delay: 2000 })
  
    htmx.on("showMessage", (e) => {
        // Remove bg-danger, if it exists
        toastElement.classList.toggle("bg-danger", false)
        toastElement.classList.add("bg-success")
        toastBody.innerText = e.detail.value
        toast.show()
    })

    // Show 'cancelled' toast on closed modal
    htmx.on("hidden.bs.modal", () => {
        // Only show the 'cancelled' toast if it isn't already shown (e.g. by
        // the 'success' function above)
        if (!toast.isShown()) {
            // Remove bg-success, if it exists
            toastElement.classList.toggle("bg-success", false)
            toastElement.classList.add("bg-danger")
            toastBody.innerText = "'Apply Now' cancelled"
            toast.show()
        }
    })
  })()
  