// Isolated, checked build extension. Never edits upstream source on disk.
// Only presentation labels and EditorJS's supported i18n configuration change.
export function localizationPlugin() {
  const touched = new Set()
  const editorHelper = ['<script setup lang="ts">', '<script setup lang="ts">\nconst __ = window.overULocalizeText\n']
  const rules = {
    'pages/Courses/CourseDashboard.vue': [
      [":title=\"__('Enrolled')\"", ":title=\"__('Students')\""],
      ["label: __('Name')", "label: __('Student')"],
      ["{{ row.name.split('(')[0] }}", "{{ __(row.name.split('(')[0].trim()) }}"],
      ['data: chartDetails.data?.progress_distribution || [],', 'data: (chartDetails.data?.progress_distribution || []).map(row => ({ ...row, name: __(row.name) })),'],
    ],
    'components/InputLabeling/RequiredIndicator.vue': [
      editorHelper, ['(required)</span>', "({{ __('required') }})</span>"],
    ],
    'components/Select/Select.vue': [
      editorHelper,
      ["placeholder: 'Select option'", "placeholder: () => window.overULocalizeText('Select option')"],
      ["emptyText: 'No options'", "emptyText: () => window.overULocalizeText('No options')"],
    ],
    'pages/Assignments.vue': [
      ['<div v-else>{{ value }}</div>', "<div v-else>{{ column.key === 'type' ? __(value) : value }}</div>"],
    ],
    'components/Assignment.vue': [
      ['{{ submissionResource.doc?.status }}', '{{ __(submissionResource.doc?.status) }}'],
      ...['Not Graded', 'Pass', 'Fail'].map(value => [`label: '${value}'`, `label: __('${value}')`]),
    ],
    'pages/AssignmentSubmissionList.vue': [
      // First interpolation is the status badge; the next is authored row data.
      ['{{ value }}', '{{ __(value) }}'],
      ...['Member', 'Assignment', 'Submitted', 'Status', 'Pass', 'Fail', 'Not Graded'].map(value => [`label: '${value}'`, `label: __('${value}')`]),
    ],
    'components/BlockEditor.vue': [
      ["i18n: {", "i18n: { messages: window.overUEditorMessages || {},"],
    ],
    'pages/Forms/AssignmentForm.vue': ['Image', 'Document', 'Text', 'URL'].map(value => [`label: '${value}'`, `label: __('${value}')`]),
    'utils/dayjs.js': [
      ["import 'dayjs/esm/locale/ur'", "import 'dayjs/esm/locale/ur'\nimport 'dayjs/esm/locale/ru'"],
      ['export default dayjs', "if (window.lang === 'ru') dayjs.locale('ru')\nexport default dayjs"],
    ],
    'utils/plyr.js': [
      ['const player = new Plyr(video, {', 'const player = new Plyr(video, { i18n: window.overUPlyrMessages || {},'],
    ],
    'components/RichTextEditor.vue': [
      ['const toolbar = [', 'const toolbar = window.overULocalizeToolbar(['],
      ['\tRedo,\n]', '\tRedo,\n])'],
    ],
    'molecules/editor/extensions/iframe/IframeInsertDialog.vue': [
      editorHelper,
      ['URL or Embed Code', "{{ __('URL or Embed Code') }}"],
      ['{{ dialog.urlError.value }}', '{{ __(dialog.urlError.value) }}'],
      ['✓ Valid {{ dialog.platformName.value }} URL', "✓ {{ __('Valid {0} URL').format(__(dialog.platformName.value)) }}"],
      ['>Cancel</Button>', ">{{ __('Cancel') }}</Button>"],
      ["{{ isEditing ? 'Update Embed' : 'Insert Embed' }}", "{{ __(isEditing ? 'Update Embed' : 'Insert Embed') }}"],
      ["return 'Edit Embed'", "return __('Edit Embed')"],
      ['`Embed ${platformConfig.value.name}`', "__('Embed {0}').format(platformConfig.value.name)"],
      [": 'Insert Embed'", ": __('Insert Embed')"],
      ["'https://youtube.com/watch?v=… or <iframe src=…>'", "__('https://youtube.com/watch?v=… or <iframe src=…>')"],
    ],
    'molecules/editor/components/EditorPopover.vue': [editorHelper, [':aria-label="dialogLabel"', ':aria-label="__(dialogLabel)"']],
    'molecules/editor/extensions/link/LinkEditorPopup.vue': [
      editorHelper,
      ...['Remove link', 'Apply', 'Copy link'].map(text => [`tooltip="${text}"`, `:tooltip="__('${text}')"`]),
      ['>Edit</Button>', ">{{ __('Edit') }}</Button>"],
    ],
    'molecules/editor/components/font-color/ColorSwatchGrid.vue': [
      editorHelper, [':text="swatch.label"', ':text="__(swatch.label)"'], [':aria-label="swatch.label"', ':aria-label="__(swatch.label)"'],
    ],
    'molecules/editor/components/table-size-picker/TableSizePicker.vue': [
      editorHelper,
      [':aria-label="`Table size, ${rows} rows by ${cols} columns`"', ':aria-label="__(\'Table size, {0} rows by {1} columns\').format(rows, cols)"'],
    ],
    'molecules/editor/components/font-color/fontColorController.ts': [
      ["import", "const __ = window.overULocalizeText\nimport"],
      ["'Text Color'", "__('Text Color')"], ["'Background Color'", "__('Background Color')"],
    ],
  }
  return {
    name: 'over-u-localization', enforce: 'pre',
    transform(code, id) {
      if (id.includes('?')) return
      const file = Object.keys(rules).find(file => id.endsWith('/src/' + file))
      if (!file) return
      for (const [before, after] of rules[file]) {
        if (!code.includes(before)) throw new Error(`OVER U locale extension needs review after upstream change: ${file}: ${before}`)
        code = code.replace(before, after)
      }
      touched.add(file)
      return {code, map: null}
    },
    buildEnd(error) {
      if (!error && Object.keys(rules).some(file => !touched.has(file))) throw new Error('OVER U locale extension did not visit all required upstream components')
    },
  }
}
