const modalForm = new bootstrap.Modal(document.getElementById('modal-form'));

document.addEventListener("DOMContentLoaded", function () {
  loadDatePicker();
});

htmx.on("htmx:afterSwap", (e) => {
  loadToolTip();
  loadDatePicker();
  loadInputmask();

  if (e.detail.target.id === "modal-form-dialog") {
    modalForm.show();
  }
})

htmx.on("htmx:beforeSwap", (e) => {
  if (e.detail.target.id === "modal-form-dialog" && e.detail.xhr.status === 204) {
    modalForm.hide();
  }
})

document.addEventListener("ObjectAdded", (e) => {
  swalSuccess.fire({
    title: e.detail.value
  })
})
document.addEventListener("ObjectDeleted", (e) => {
  swalSuccess.fire({
    title: e.detail.value
  })
})
document.addEventListener("ObjectEdited", (e) => {
  swalSuccess.fire({
    title: e.detail.value
  })
})
document.addEventListener("PasswordUpdated", (e) => {
  swalSuccess.fire({
    title: e.detail.value
  })
})
document.addEventListener("ObjectNotDeleted", (e) => {
  swalError.fire({
    text: e.detail.value,
  })
})
document.addEventListener("CommentAdded", (e) => {
  swalSuccess.fire({
    text: e.detail.value,
  })
})
document.addEventListener("ObjectsImported", (e) => {
  swalSuccess.fire({
    text: e.detail.value,
  })
})

document.addEventListener("shown.bs.modal", () => {
  const btnEnviar = document.getElementById("btn-modal-enviar");
  const modalForm = document.querySelector(".modal form");
  if (modalForm && btnEnviar) {
    modalForm.addEventListener("submit", (e) => {
      btnEnviar.disabled = true;
      btnEnviar.querySelector(".sent").classList.remove("d-none");
      btnEnviar.querySelector(".unsent").classList.add("d-none");
    })
  }

})
