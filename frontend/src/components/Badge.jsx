import React from 'react'

const LABELS = {
  critical: 'Critical',
  high: 'High / Under Review',
  medium: 'Medium',
  needs_review: 'Under Review',
  reviewed: 'Resolved',
  dismissed: 'Dismissed',
}

export default function Badge({ value }) {
  if (!value) return null
  return <span className={`badge ${value}`}>{LABELS[value] || value}</span>
}
