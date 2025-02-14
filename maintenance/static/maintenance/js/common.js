let tooltipList = [];

function loadToolTip() {
  [...tooltipList].forEach(e => e.dispose());
  tooltipList = [];
  document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(e => {
    tooltipList.push(new bootstrap.Tooltip(e));
  })
}

let allDatePickers = [];
const dateOpts = {
  buttonClass: "btn",
  language: "es"
}

function loadDatePicker() {
  [...allDatePickers].forEach(e => e.destroy());
  allDatePickers = [];

  document.querySelectorAll("input[data-date-picker='true']").forEach(e => {
    let setMinDays = e.dataset.setMinDays;
    if (setMinDays) {
      const dateOptsNew = {...dateOpts};
      dateOptsNew.minDate = new Date();
      allDatePickers.push(new Datepicker(e, dateOptsNew));
    } else {
      allDatePickers.push(new Datepicker(e, dateOpts));
    }

  })
}

const cellInputmask = new Inputmask({
  mask: "999999999",
})

const onlyNumbersInputmask = new Inputmask({
  mask: "99999999[999999999]",
  placeholder: ""
})

function loadInputmask() {
  const allCellInput = document.querySelectorAll("input[data-cell-input='true']");
  const allNumberInput = document.querySelectorAll("input[data-number-input='true']");
  allCellInput.forEach(e => {
    cellInputmask.mask(e);
  })

  allCellInput.forEach(e => {
    e.addEventListener("input", () => {
      if (!e.value.startsWith("9")) {
        e.value = "9";
      }
    })
  })

  allNumberInput.forEach(e => {
    onlyNumbersInputmask.mask(e);
  })
}

function divSetRequired(div, value) {
  const isSelect = div.querySelector("select")
  if (isSelect) {
    isSelect.required = value;
  } else {
    div.querySelector("input").required = value;
  }
}

function divSetValue(div, value) {
  const isSelect = div.querySelector("select")
  if (isSelect) {
    isSelect.value = value;
  } else {
    div.querySelector("input").value = value;
  }
}

function seekAndShow(el, val, dst, def = "") {
  if (el.value === val) {
    dst.classList.remove("d-none");
    if (def) {
      divSetValue(dst, def);
    }
  } else {
    dst.classList.add("d-none");
    divSetValue(dst, "");
  }
}

const swalDelete = Swal.mixin({
  customClass: {
    confirmButton: 'btn btn-danger ms-md-5',
    cancelButton: 'btn btn-secondary me-sm-5'
  },
  buttonsStyling: false,
  icon: "warning",
  showCancelButton: true,
  confirmButtonText: "Eliminar",
  cancelButtonText: "Cancelar",
  reverseButtons: true,
  title: "¿Está seguro?",
  text: "Se eliminará el registro seleccionado"
});

const swalSuccess = Swal.mixin({
  icon: "success",
  timer: 2000,
  showConfirmButton: false
});

const swalError = Swal.mixin({
  icon: "error",
  title: "Se ha producido un error",
  showConfirmButton: false,
  showCancelButton: true
});
