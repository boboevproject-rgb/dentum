"""Lab work orders sent to external laboratories for patients."""

from fastapi import APIRouter

from app.core.plugins import BaseModule

from .models import LabOrder, LabOrderEvent
from .router import router


class LabOrdersModule(BaseModule):
    """Lab work order tracking, linked to patients and external contacts."""

    manifest = {
        "name": "lab_orders",
        "version": "0.2.0",
        "summary": "Track lab work orders per patient — from sent to received.",
        "author": "DentalPin Core Team",
        "license": "BSL-1.1",
        "category": "community",
        "depends": ["patients", "contacts"],
        "installable": True,
        "auto_install": False,
        "removable": True,
        "role_permissions": {
            "admin": ["*"],
            "dentist": ["read", "write", "comment"],
            "hygienist": ["read"],
            "assistant": ["read", "write", "comment"],
            "receptionist": ["read", "write", "comment"],
            # Dental technician: sees every lab order of the clinic, moves
            # them along the lab workflow and talks to the clinic in the
            # order thread. Cannot create, receive or cancel orders.
            "technician": ["read", "work", "comment"],
        },
        "frontend": {
            "layer_path": "frontend",
            "navigation": [
                {
                    "label": "nav.labOrdersForm",
                    "section": "lab",
                    "icon": "i-lucide-clipboard-plus",
                    "to": "/lab-orders/new",
                    "permission": "lab_orders.write",
                    "order": 92,
                },
                {
                    "label": "nav.labWorkbench",
                    "section": "lab",
                    "icon": "i-lucide-hammer",
                    "to": "/lab-workbench",
                    "permission": "lab_orders.work",
                    "order": 91,
                },
                {
                    "label": "nav.labOrdersStatus",
                    "section": "lab",
                    "icon": "i-lucide-flask-conical",
                    "to": "/lab-orders",
                    "permission": "lab_orders.read",
                    "order": 92.5,
                },
            ],
        },
    }

    def get_models(self) -> list:
        return [LabOrder, LabOrderEvent]

    def get_router(self) -> APIRouter:
        return router

    def get_permissions(self) -> list[str]:
        return ["read", "write", "work", "comment"]

    def get_tools(self) -> list:
        from . import tools

        return tools.get_tools()
