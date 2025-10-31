// Maneja la división automática entre personas (cuando se presiona "Dividir igual")
function dividirIgual() {
  const totalInput = document.getElementById('montoTotal');
  let total = parseFloat(totalInput.value.replace(/,/g, '')) || 0;
  const inputs = document.querySelectorAll('[name^="monto_"]');
  if(inputs.length === 0 || total === 0) return;

  const division = Math.floor((total / inputs.length) * 100) / 100; // evita decimales infinitos
  let acumulado = 0;

  inputs.forEach((i, idx) => {
    let value = division;
    acumulado += division;
    // Ajusta la última persona para que sume exactamente el total
    if(idx === inputs.length - 1){
      value = total - (acumulado - division);
    }
    i.value = value.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
    const id = i.name.split('_')[1];
    calcularFalta(id);
  });
}

// Toggle estado con request fetch (ajax)
async function toggleDetalle(detalleId, btn) {
  try {
    const resp = await fetch(`/api/detalle/${detalleId}/toggle`, { method: 'POST' });
    const data = await resp.json();
    if (data && data.estado) {
      btn.textContent = data.estado;
      btn.classList.toggle('btn-success', data.estado === 'Pagado');
      btn.classList.toggle('btn-outline-secondary', data.estado === 'Debe');
    }
  } catch (e) {
    console.error(e);
  }
}
