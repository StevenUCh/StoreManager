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

function dividirSeleccionadas() {
  const totalInput = document.getElementById('montoTotal');
  let total = parseInt(totalInput.value.replace(/,/g, '')) || 0; // total entero
  
  const checkboxes = document.querySelectorAll('.person-checkbox:checked');
  if (checkboxes.length === 0) return;

  const base = Math.floor(total / checkboxes.length); // división entera
  let acumulado = 0;

  checkboxes.forEach((cb, idx) => {
    const personId = cb.dataset.personId;
    let value = base;
    acumulado += base;

    // Última persona → ajuste del sobrante
    if (idx === checkboxes.length - 1) {
      value = total - (acumulado - base);
    }

    const montoInput = document.querySelector(`[name="monto_${personId}"]`);
    montoInput.value = value.toLocaleString('en-US'); // sin decimales

    calcularFalta(personId);
  });
}


function toggleDividirButton() {
  const checkboxes = document.querySelectorAll('.person-checkbox');
  const btn = document.getElementById('btnDividir');
  btn.disabled = !Array.from(checkboxes).some(cb => cb.checked);
}

document.querySelectorAll('.person-checkbox').forEach(cb => {
  const span = cb.nextElementSibling;
  
  // Inicializar el estado visual
  toggleCheckmark(cb, span);

  cb.addEventListener('change', () => {
    toggleCheckmark(cb, span);
    toggleDividirButton();
  });
});

function toggleCheckmark(checkbox, span) {
  const svg = span.querySelector('svg');
  if(checkbox.checked){
    svg.classList.remove('hidden');
    span.classList.add('bg-indigo-600', 'border-indigo-600');
  } else {
    svg.classList.add('hidden');
    span.classList.remove('bg-indigo-600', 'border-indigo-600');
  }
}

document.addEventListener('DOMContentLoaded', function () {

  // Event delegation: escucha clicks en cualquier badge
  document.body.addEventListener('click', function (e) {
    const badge = e.target.closest('.pago-badge');
    if (!badge) return;

    const personId = badge.dataset.personId;
    togglePagoBadge(personId, badge);
  });

  // Inicializa visual según hidden inputs (útil si hay estado previo)
  document.querySelectorAll('.pago-hidden').forEach(h => {
    const pid = h.dataset.personId;
    const badge = document.querySelector(`.pago-badge[data-person-id="${pid}"]`);
    if (h.value === '1') applyBadgeActive(badge);
    else applyBadgeInactive(badge);
  });

  // Función para alternar el badge y el hidden input
  function togglePagoBadge(personId, badgeEl) {
    const hidden = document.querySelector(`.pago-hidden[data-person-id="${personId}"]`);
    if (!hidden || !badgeEl) return;

    const isActive = badgeEl.classList.contains('bg-green-600');
    if (isActive) {
      applyBadgeInactive(badgeEl);
      hidden.value = '0';
      unfilledInputsPago(personId);
    } else {
      applyBadgeActive(badgeEl);
      hidden.value = '1';
      filledInputsPago(personId);
    }
    marcarPagadoVisual(personId);
  }

  function applyBadgeActive(badgeEl) {
    badgeEl.classList.add('bg-green-600','border-green-600','text-white');
    badgeEl.classList.remove('bg-gray-100','dark:bg-gray-800','text-gray-700','dark:text-gray-200');
  }

  function applyBadgeInactive(badgeEl) {
    badgeEl.classList.remove('bg-green-600','border-green-600','text-white');
    badgeEl.classList.add('bg-gray-100','dark:bg-gray-800','text-gray-700','dark:text-gray-200');
  }

}); // DOMContentLoaded end

function filledInputsPago(personId){
  const estadoSelect = document.querySelector(`[name="estado_${personId}"]`);
  const montoInput = document.querySelector(`[name="monto_${personId}"]`);
  const abonadoInput = document.querySelector(`[name="abonado_${personId}"]`);
  const faltaInput = document.getElementById(`falta_${personId}`);

  abonadoInput.value = montoInput.value;
  estadoSelect.value = 'Pagado'
  faltaInput.value =  0;
}

function unfilledInputsPago(personId){
  const estadoSelect = document.querySelector(`[name="estado_${personId}"]`);
  const montoInput = document.querySelector(`[name="monto_${personId}"]`);
  const abonadoInput = document.querySelector(`[name="abonado_${personId}"]`);
  const faltaInput = document.getElementById(`falta_${personId}`);

  abonadoInput.value = 0;
  estadoSelect.value = 'Debe'
  faltaInput.value =  montoInput.value;
}

// Mantén tu función marcarPagadoVisual (sólo afecta "falta")
function marcarPagadoVisual(personId){
  const estadoSelect = document.querySelector(`[name="estado_${personId}"]`);
  const montoInput = document.querySelector(`[name="monto_${personId}"]`);
  const abonadoInput = document.querySelector(`[name="abonado_${personId}"]`);
  const faltaInput = document.getElementById(`falta_${personId}`);

  if(!faltaInput) return;

  if(estadoSelect && estadoSelect.value === 'Pagado'){
    faltaInput.value = 0;
    faltaInput.classList.add('bg-green-100', 'dark:bg-green-700', 'text-green-800', 'dark:text-green-200');
  } else {
    const totalMonto = parseFloat((montoInput && montoInput.value || '').toString().replace(/,/g, '')) || 0;
    const abonado = parseFloat((abonadoInput && abonadoInput.value || '').toString().replace(/,/g, '')) || 0;
    faltaInput.value = (totalMonto - abonado).toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:2});
    faltaInput.classList.remove('bg-green-100', 'dark:bg-green-700', 'text-green-800', 'dark:text-green-200');
  }
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
