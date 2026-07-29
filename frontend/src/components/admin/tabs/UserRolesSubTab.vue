<template>
  <div>
    <h3 class="text-xl font-bold mb-2">الأدوار المتاحة في النظام</h3>
    <p class="text-sm text-gray-500 mb-6">
      عرض توضيحي فقط. إضافة دور جديد تتطلب تعديل من فريق التطوير لأن الأدوار مرتبطة ببنية قاعدة البيانات.
    </p>

    <div class="space-y-3">
      <div v-for="role in roles" :key="role.value" class="flex items-center justify-between p-4 border-2 border-gray-100 rounded-2xl">
        <div class="flex items-center gap-3">
          <span class="text-2xl">{{ role.icon }}</span>
          <div>
            <div class="font-bold text-gray-800">{{ role.label }}</div>
            <div class="text-xs text-gray-400">{{ role.description }}</div>
          </div>
        </div>
        <span class="text-xs bg-gray-50 text-gray-500 px-3 py-1 rounded-full font-mono">{{ role.value }}</span>
      </div>
    </div>

    <div class="mt-6 p-4 bg-amber-50 text-amber-700 text-sm rounded-2xl">
      💡 هل تحتاج دورًا جديدًا (مثل "محاسب" أو "مشرف ورشة")؟ تواصل مع فريق التطوير لإضافته بأمان.
    </div>
  </div>
</template>

<script setup>
const roles = [
  { value: 'admin', label: 'مدير (Admin)', icon: '👑', description: 'صلاحيات كاملة على كل أجزاء النظام بدون استثناء' },
  { value: 'supervisor', label: 'مشرف', icon: '🧑‍💼', description: 'كل الصلاحيات التشغيلية، ما عدا حذف/تعطيل المستخدمين' },
  { value: 'operator', label: 'مسيّر', icon: '👷', description: 'الوصول فقط لتبويبي الورشة والأعطال' },
]
</script>