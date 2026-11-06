export function scannedCard(code, classId) {
  try {
    const payload = JSON.parse(code.data);
    if (payload.app !== 'classpulse' || payload.class_id !== classId || !payload.student_id) return null;
    const { topLeftCorner: left, topRightCorner: right } = code.location;
    const quarter = Math.round(Math.atan2(right.y - left.y, right.x - left.x) / (Math.PI / 2));
    return { student_id: payload.student_id, option: ((-quarter % 4) + 4) % 4 };
  } catch { return null; }
}
