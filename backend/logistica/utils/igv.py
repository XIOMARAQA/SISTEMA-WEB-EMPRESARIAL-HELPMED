from decimal import Decimal, ROUND_HALF_UP

IGV_TASA = Decimal('0.18')
IGV_FACTOR = Decimal('1.18')


def calcular_linea(cantidad, precio_unitario, igv_incluido=False):
    """Calcula subtotal (sin IGV), IGV e importe total de una línea."""
    cantidad = Decimal(str(cantidad or 0))
    precio = Decimal(str(precio_unitario or 0))
    if igv_incluido:
        importe_total = (precio * cantidad).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        subtotal = (importe_total / IGV_FACTOR).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        igv = (importe_total - subtotal).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    else:
        subtotal = (precio * cantidad).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        igv = (subtotal * IGV_TASA).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        importe_total = (subtotal + igv).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return subtotal, igv, importe_total
