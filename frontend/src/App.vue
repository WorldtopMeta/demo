<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="topbar-inner">
        <div class="brand">
          <div class="brand-icon">DB</div>
          <div>
            <div style="font-weight: 700">LPI Trade Data Query Tool</div>
            <div style="font-size: 11px; color: var(--muted)">Trade Analytics Platform</div>
          </div>
        </div>
        <el-tag type="primary">AI Assistant Active</el-tag>
      </div>
    </header>

    <main class="main">
      <section class="card">
        <div class="card-body">
          <el-form @submit.prevent>
            <el-form-item label="Natural Language Question">
              <el-input
                v-model="question"
                type="textarea"
                :rows="4"
                :placeholder="placeholderText"
              />
            </el-form-item>
            <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px">
              <el-button
                v-for="item in suggestions"
                :key="item"
                text
                bg
                @click="question = item"
              >
                {{ item }}
              </el-button>
            </div>
            <div style="display: flex; gap: 10px; align-items: center">
              <el-button type="primary" :loading="loading" @click="executeQuery">Execute Query</el-button>
              <el-alert
                v-if="meta?.assumptions?.length"
                type="info"
                :closable="false"
                show-icon
                style="padding: 6px 10px"
              >
                <template #title>
                  Assumptions: {{ meta.assumptions.join(' | ') }}
                </template>
              </el-alert>
            </div>
          </el-form>
        </div>
      </section>

      <section class="card">
        <div class="card-body">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px">
            <strong>Generated SQL Query</strong>
            <el-button text @click="copySql" :disabled="!sql">Copy SQL</el-button>
          </div>
          <div class="sql-view mono">{{ sql || noSqlText }}</div>
          <div v-if="meta" style="margin-top: 10px; color: var(--muted); font-size: 13px">
            confidence: {{ Number(meta.confidence || 0).toFixed(2) }} | rows: {{ meta.row_count }}
            <span v-if="meta.default_limit_applied">| default LIMIT applied</span>
            <span v-if="meta.notes">| notes: {{ meta.notes }}</span>
          </div>
        </div>
      </section>

      <section class="card">
        <div class="card-body">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px">
            <strong>Query Results</strong>
            <el-button text :disabled="!rows.length" @click="exportCsv">Export CSV</el-button>
          </div>

          <el-alert v-if="error" type="error" :title="error" show-icon :closable="false" style="margin-bottom: 10px" />

          <el-table :data="rows" stripe border v-loading="loading" style="width: 100%" :empty-text="emptyTableText">
            <el-table-column
              v-for="column in columns"
              :key="column"
              :prop="column"
              :label="column"
              min-width="160"
              show-overflow-tooltip
            />
          </el-table>
        </div>
      </section>
    </main>

    <footer class="footer">Powered by Supabase + OpenRouter LLM</footer>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

interface QueryMeta {
  row_count: number
  confidence: number
  notes: string
  assumptions: string[]
  default_limit_applied: boolean
}

interface QueryResponse {
  sql: string
  columns: string[]
  rows: Record<string, unknown>[]
  meta: QueryMeta
}

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

const placeholderText = '\u4f8b\u5982\uff1a\u4e9e\u6d32\u54ea\u4e9b\u570b\u5bb6\u7684 LPI > 3.0'
const noSqlText = '\u5c1a\u672a\u57f7\u884c\u67e5\u8a62\u3002'
const emptyTableText = '\u7121\u8cc7\u6599'
const warningInputRequired = '\u8acb\u5148\u8f38\u5165\u554f\u984c'
const queryFailedText = '\u67e5\u8a62\u5931\u6557'
const unknownErrorText = '\u672a\u77e5\u932f\u8aa4'

const suggestions = [
  '\u4e9e\u6d32\u54ea\u4e9b\u570b\u5bb6\u7684 LPI > 3.0',
  '\u5404\u5340\u57df\u5e73\u5747 LPI',
  '\u7269\u6d41\u8868\u73fe\u524d\u4e94\u540d',
]

const question = ref('\u4e9e\u6d32\u54ea\u4e9b\u570b\u5bb6\u7684 LPI > 3.0')
const loading = ref(false)
const sql = ref('')
const columns = ref<string[]>([])
const rows = ref<Record<string, unknown>[]>([])
const meta = ref<QueryMeta | null>(null)
const error = ref('')

async function executeQuery() {
  if (!question.value.trim()) {
    ElMessage.warning(warningInputRequired)
    return
  }

  loading.value = true
  error.value = ''

  try {
    const response = await fetch(`${API_BASE}/api/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: question.value }),
    })

    const data = await response.json()
    if (!response.ok) {
      throw new Error(data?.detail || queryFailedText)
    }

    const result = data as QueryResponse
    sql.value = result.sql
    columns.value = result.columns
    rows.value = result.rows
    meta.value = result.meta
  } catch (err) {
    const message = err instanceof Error ? err.message : unknownErrorText
    error.value = message
    ElMessage.error(message)
  } finally {
    loading.value = false
  }
}

async function copySql() {
  if (!sql.value) return
  await navigator.clipboard.writeText(sql.value)
  ElMessage.success('SQL copied')
}

function exportCsv() {
  if (!rows.value.length || !columns.value.length) return

  const head = columns.value.join(',')
  const body = rows.value
    .map((row) =>
      columns.value
        .map((col) => {
          const value = row[col] ?? ''
          return `"${String(value).replaceAll('"', '""')}"`
        })
        .join(','),
    )
    .join('\n')

  const csv = `${head}\n${body}`
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'query_result.csv'
  link.click()
  URL.revokeObjectURL(url)
}
</script>
