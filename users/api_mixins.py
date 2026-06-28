class OrganizationViewSetMixin:
    def get_queryset(self):
        qs = super().get_queryset()
        org = getattr(self.request, "organization", None)
        if org is None:
            return qs.none()
        return qs.filter(organization=org)

    def perform_create(self, serializer):
        save_kwargs = {"organization": self.request.organization}
        model = serializer.Meta.model
        if any(f.name == "created_by" for f in model._meta.fields):
            save_kwargs["created_by"] = self.request.user
        serializer.save(**save_kwargs)
