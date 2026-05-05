import {
  LayoutGrid,
  Users,
  Calendar,
  Building2,
  Settings,
  Palette,
  Bot,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

export type PrimaryNavItem = {
  id: string
  label: string
  icon: LucideIcon
}

/** Active primary rail item on the bug chatbot route. */
export const ACTIVE_PRIMARY_NAV_ID = 'bug-chatbot'

export const PRIMARY_NAV: PrimaryNavItem[] = [
  { id: 'dashboards', label: 'Dashboards', icon: LayoutGrid },
  { id: 'patients', label: 'Patients', icon: Users },
  { id: 'appointments', label: 'Appointments', icon: Calendar },
  { id: 'rooms', label: 'Rooms', icon: Building2 },
  { id: 'customization', label: 'Customization', icon: Palette },
  { id: 'bug-chatbot', label: 'Bug report', icon: Bot },
  { id: 'settings', label: 'Settings', icon: Settings },
]
