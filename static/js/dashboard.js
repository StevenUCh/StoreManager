document.addEventListener("DOMContentLoaded", () => {
  const ctx1 = document.getElementById('chartIngresosGastos');
  const ctx2 = document.getElementById('chartCategorias');

  if (ctx1 && ingresosGastosData) {
    new Chart(ctx1, {
      type: 'line',
      data: {
        labels: ingresosGastosData.labels,
        datasets: [
          {
            label: 'Ingresos',
            data: ingresosGastosData.ingresos,
            borderColor: 'rgb(34,197,94)',
            tension: 0.3,
            fill: false
          },
          {
            label: 'Gastos',
            data: ingresosGastosData.gastos,
            borderColor: 'rgb(239,68,68)',
            tension: 0.3,
            fill: false
          }
        ]
      },
      options: { responsive: true, plugins: { legend: { position: 'top' } } }
    });
  }

  if (ctx2 && categoriasData) {
    new Chart(ctx2, {
      type: 'doughnut',
      data: {
        labels: categoriasData.labels,
        datasets: [{
          data: categoriasData.valores,
          backgroundColor: ['#60a5fa', '#34d399', '#fbbf24', '#f87171', '#a78bfa']
        }]
      },
      options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
    });
  }
});


document.addEventListener("click", function (e) {
    const btn = e.target.closest(".ajax-page");
    if (!btn) return;

    e.preventDefault();

    const url = btn.getAttribute("href");
    const spinner = document.querySelector("#spinner-pagination");
    const paginacionWrapper = document.querySelector("#paginacion-wrapper");
    const tableContainer = document.querySelector("#tabla-movimientos");

    // 1. Ocultar los botones de paginación
    paginacionWrapper.classList.add("hidden");

    // 2. Mostrar el spinner en su lugar
    spinner.classList.remove("hidden");

    fetch(url)
        .then(res => res.text())
        .then(html => {
            tableContainer.innerHTML = html;
        })
        .catch(err => console.error("Error cargando tabla AJAX:", err))
        .finally(() => {
            // 3. Ocultar spinner
            spinner.classList.add("hidden");

            // 4. Restaurar botones de paginación
            paginacionWrapper.classList.remove("hidden");
        });
});
