// مصدر واحد للحقيقة لكتالوج التبويبات (id/label/icon فقط)
// صلاحيات كل دور أصبحت ديناميكية الآن، تُدار من الباك إند (جدول roles)
// وتصل مع بيانات المستخدم كحقل allowed_tabs

export const TAB_DEFINITIONS = [
  { id: 'stats',     label: 'الإحصائيات',    icon: '📈' },
  { id: 'users',     label: 'المستخدمون',     icon: '👤' },
  { id: 'settings',  label: 'الإعدادات',      icon: '🛠️' },
  { id: 'assembly',  label: 'الورشة',         icon: '⚙️' },
  { id: 'sales',     label: 'المبيعات',       icon: '💰' },
  { id: 'faults',    label: 'الأعطال',        icon: '⚠️' },
  { id: 'workers',   label: 'العمال',         icon: '👷' },
  { id: 'customers', label: 'العملاء',        icon: '🧑‍🤝‍🧑' },
]

const ALL_TAB_IDS = TAB_DEFINITIONS.map(t => t.id)

// 🛡️ admin دائمًا بكل الصلاحيات بغض النظر عمّا هو مخزّن فعليًا
// (حماية من قفل النظام بالكامل بالخطأ عبر تبويب إدارة الأدوار)
function resolveAllowedIds(role, allowedTabs) {
  if (role === 'admin') return ALL_TAB_IDS
  return Array.isArray(allowedTabs) ? allowedTabs : []
}

// أول تبويب مسموح به (يُستخدم كتبويب افتراضي عند الدخول)
export function getDefaultTab(role, allowedTabs) {
  const ids = resolveAllowedIds(role, allowedTabs)
  const allowed = TAB_DEFINITIONS.find(t => ids.includes(t.id))
  return allowed ? allowed.id : null
}

// هل هذا التبويب مسموح لهذا المستخدم؟
export function isTabAllowed(tabId, role, allowedTabs) {
  const ids = resolveAllowedIds(role, allowedTabs)
  return ids.includes(tabId)
}

// قائمة التبويبات المسموحة (تُستخدم في القائمة الجانبية)
export function getAllowedTabs(role, allowedTabs) {
  const ids = resolveAllowedIds(role, allowedTabs)
  return TAB_DEFINITIONS.filter(t => ids.includes(t.id))
}