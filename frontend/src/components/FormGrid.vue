<template>
  <div class="form-grid">
    <div v-for="f in fields" :key="f.key" class="field" :class="{ wide: f.wide }">
      <label :for="'f-' + f.key">{{ f.label }}<span v-if="f.required" class="req"> *</span></label>
      <select v-if="f.type === 'select'" :id="'f-' + f.key" v-model="model[f.key]">
        <option v-if="!f.required" value="">-- Select --</option>
        <option v-for="o in f.options" :key="o.value ?? o" :value="o.value ?? o">{{ o.label ?? o }}</option>
      </select>
      <textarea v-else-if="f.type === 'textarea'" :id="'f-' + f.key" v-model="model[f.key]" rows="2"></textarea>
      <input v-else :id="'f-' + f.key" v-model="model[f.key]" :type="f.type || 'text'"
        :placeholder="f.placeholder || ''" :step="f.type === 'number' ? 'any' : undefined"
        :list="f.list ? 'dl-' + f.key : undefined" />
      <datalist v-if="f.list" :id="'dl-' + f.key">
        <option v-for="o in f.list" :key="o" :value="o" />
      </datalist>
      <small v-if="f.help" class="help">{{ f.help }}</small>
    </div>
  </div>
</template>

<script setup>
defineProps({ fields: Array, model: Object })
</script>
