import { useState } from 'react';

export default function EditableTableRow({ ViewComponent, EditComponent, onSave, onCancel, defaultEditing = false }) {
  const [isEditing, setIsEditing] = useState(defaultEditing);
  const [isSaving, setIsSaving] = useState(false);

  async function handleSave(data) {
    setIsSaving(true);
    try {
      if (onSave) {
        await onSave(data);
      }
      setIsEditing(false);
    } finally {
      setIsSaving(false);
    }
  }

  function handleCancel() {
    setIsEditing(false);
    if (onCancel) onCancel();
  }

  return isEditing ? (
    <tr className="editable-row-editing">
      <EditComponent onSave={handleSave} onCancel={handleCancel} isSaving={isSaving} />
    </tr>
  ) : (
    <tr className="editable-row-view">
      <ViewComponent onEdit={() => setIsEditing(true)} />
    </tr>
  );
}
