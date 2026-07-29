// مصدر واحد للحقيقة لمصفوفة صلاحيات التبويبات
// يُستخدم في DashboardView.vue (إخفاء التبويبات) وفي index.js (route guard)
// أي تعديل مستقبلي على الصلاحيات يكفي أن يتم هنا فقط

export const TAB_DEFINITIONS = [
  { id: 'dashboard', label: 'الإحصائيات',    icon: '📈', roles: ['admin', 'supervisor'] },
  { id: 'users',     label: 'المستخدمون',     icon: '👤', roles: ['admin', 'supervisor'] },
  { id: 'settings',  label: 'الإعدادات',      icon: '🛠️', roles: ['admin', 'supervisor'] },
  { id: 'assembly',  label: 'الورشة',         icon: '⚙️', roles: ['admin', 'supervisor', 'operator'] },
  { id: 'sales',     label: 'المبيعات',       icon: '💰', roles: ['admin', 'supervisor'] },
  { id: 'faults',    label: 'الأعطال',        icon: '⚠️', roles: ['admin', 'supervisor', 'operator'] },
  { id: 'workers',   label: 'العمال',         icon: '👷', roles: ['admin', 'supervisor'] },
  { id: 'customers', label: 'العملاء',        icon: '🧑‍🤝‍🧑', roles: ['admin', 'supervisor'] },
]

// أول تبويب مسموح به لكل دور (يُستخدم كتبويب افتراضي عند الدخول)
export function getDefaultTab(role) {
  const allowed = TAB_DEFINITIONS.find(t => t.roles.includes(role))
  return allowed ? allowed.id : 'assembly'
}

// هل هذا التبويب مسموح لهذا الدور؟
export function isTabAllowed(tabId, role) {
  const tab = TAB_DEFINITIONS.find(t => t.id === tabId)
  if (!tab) return false
  return tab.roles.includes(role)
}

// قائمة التبويبات المسموحة لدور معيّن (تُستخدم في القائمة الجانبية)
export function getAllowedTabs(role) {
  return TAB_DEFINITIONS.filter(t => t.roles.includes(role))
}