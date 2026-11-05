// Keep the stored class name and identifiers intact; shorten only known
// sample-dataset labels in the interface.
export function classDisplayName(name, topic) {
  if (!name) return '';
  if (name === `${topic} Synthetic Demo Class` ||
      (topic === 'Fractions' && name === 'Synthetic Fractions demonstration') ||
      name.startsWith('Synthetic ClassPulse · ')) return topic || name;
  return name;
}
