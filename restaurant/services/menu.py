from restaurant.models import MenuCategory


class MenuService:

    def get_formatted_menu(self, restaurant):
        """Renders the restaurant's available menu as plain text grouped by
        category — meant to be dropped straight into a reply to a customer
        (e.g. by the `share_menu` agent tool), not consumed as structured
        data.
        """
        categories = (
            MenuCategory.objects.filter(restaurant=restaurant)
            .prefetch_related("items")
            .order_by("order", "name")
        )

        lines = [restaurant.name, ""]
        for category in categories:
            items = [item for item in category.items.all() if item.is_available]
            if not items:
                continue

            lines.append(category.name)
            for item in sorted(items, key=lambda item: item.name):
                line = f"- {item.name} — ${item.price}"
                if item.description:
                    line += f": {item.description}"
                lines.append(line)
            lines.append("")

        return "\n".join(lines).strip()
