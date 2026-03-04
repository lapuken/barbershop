from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction

from apps.sales.models import Sale, SaleItem

TWOPLACES = Decimal("0.01")


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def duplicate_sale_for(shop, barber, sale_date, exclude_sale_id=None):
    queryset = Sale.objects.filter(shop=shop, barber=barber, sale_date=sale_date)
    if exclude_sale_id:
        queryset = queryset.exclude(pk=exclude_sale_id)
    return queryset.first()


def recalculate_sale(sale: Sale) -> Sale:
    total = sum((item.line_total for item in sale.items.all()), Decimal("0.00"))
    sale.total_amount = quantize_money(total)
    sale.commission_amount = quantize_money(sale.total_amount * sale.barber.commission_rate / Decimal("100"))
    sale.save(update_fields=["total_amount", "commission_amount", "updated_at"])
    return sale


@transaction.atomic
def save_sale_with_items(*, sale: Sale, items_data: list[dict], user):
    sale.created_by = sale.created_by or user
    sale.updated_by = user
    sale.full_clean()
    sale.save()

    sale.items.all().delete()
    for item in items_data:
        if item.get("DELETE"):
            continue
        product = item.get("product")
        if product:
            item_name = product.name
            unit_price = product.sale_price
        else:
            item_name = item["item_name_snapshot"]
            unit_price = item["unit_price_snapshot"]
        sale_item = SaleItem(
            sale=sale,
            item_type=item["item_type"],
            product=product,
            item_name_snapshot=item_name,
            unit_price_snapshot=quantize_money(unit_price),
            quantity=item["quantity"],
        )
        sale_item.full_clean()
        sale_item.save()

    sale.refresh_from_db()
    return recalculate_sale(sale)
