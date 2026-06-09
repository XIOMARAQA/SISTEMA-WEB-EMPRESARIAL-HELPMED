const IGV = 0.18

export function calcularLinea(cantidad, precioUnitario, igvIncluido = false) {
  const cant = Number(cantidad) || 0
  const precio = Number(precioUnitario) || 0
  if (igvIncluido) {
    const importe = round2(precio * cant)
    const subtotal = round2(importe / (1 + IGV))
    const igv = round2(importe - subtotal)
    return { subtotal, igv, importe }
  }
  const subtotal = round2(precio * cant)
  const igv = round2(subtotal * IGV)
  const importe = round2(subtotal + igv)
  return { subtotal, igv, importe }
}

export function sumarTotales(items) {
  return items.reduce(
    (acc, it) => {
      const { subtotal, igv, importe } = calcularLinea(it.cantidad, it.precio_unitario, it.igv_incluido)
      acc.subtotal += subtotal
      acc.igv += igv
      acc.importe += importe
      return acc
    },
    { subtotal: 0, igv: 0, importe: 0 },
  )
}

function round2(n) {
  return Math.round(n * 100) / 100
}

export function formatoMoneda(valor) {
  return Number(valor || 0).toLocaleString('es-PE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
