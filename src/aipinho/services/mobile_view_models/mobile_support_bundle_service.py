from __future__ import annotations

from aipinho.schemas.mobile_view_models import MobileSupportBundlePreview
from aipinho.services.mobile_view_models.support_bundle_mobile_aggregator import SupportBundleMobileAggregator


class MobileSupportBundleService:
    def preview(self) -> MobileSupportBundlePreview:
        return SupportBundleMobileAggregator().preview()

