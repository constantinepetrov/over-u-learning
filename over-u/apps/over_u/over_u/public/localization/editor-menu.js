// The editor accepts menu descriptors. Copy only display labels and preserve
// actions, IDs, availability predicates and authored content unchanged.
window.overULocalizeText = text => window.__ ? window.__(text) : text
window.overULocalizeToolbar = function localizeToolbar(items) {
  const translate = window.overULocalizeText
  return items.map(item => {
    const copy = {...item}
    if (item.label) copy.label = translate(item.label)
    if (item.items) copy.items = localizeToolbar(item.items)
    if (item.getLabel) copy.getLabel = editor => translate(item.getLabel(editor))
    return copy
  })
}
