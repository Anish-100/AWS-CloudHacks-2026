import { useState } from "react";

const initialForm = {
  title: "",
  targetAmount: "",
  currentAmount: "0",
  deadline: "",
  type: "veryShort",
};

export default function GoalForm({ onCreate }) {
  const [form, setForm] = useState(initialForm);

  function updateField(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  function submitGoal(event) {
    event.preventDefault();
    if (!form.title.trim() || !form.targetAmount || !form.deadline) {
      return;
    }

    onCreate({
      title: form.title.trim(),
      targetAmount: Number(form.targetAmount),
      currentAmount: Number(form.currentAmount || 0),
      deadline: form.deadline,
      type: form.type,
      status: "pending",
    });

    setForm(initialForm);
  }

  return (
    <form className="goal-form" onSubmit={submitGoal}>
      <div className="section-heading">
        <p className="eyebrow">New goal</p>
        <h2>Give every dollar a job.</h2>
      </div>

      <label>
        Goal name
        <input name="title" value={form.title} onChange={updateField} placeholder="Save for groceries" />
      </label>

      <div className="form-grid">
        <label>
          Target
          <input
            name="targetAmount"
            value={form.targetAmount}
            onChange={updateField}
            min="1"
            type="number"
            placeholder="150"
          />
        </label>
        <label>
          Saved
          <input name="currentAmount" value={form.currentAmount} onChange={updateField} min="0" type="number" />
        </label>
      </div>

      <div className="form-grid">
        <label>
          Deadline
          <input name="deadline" value={form.deadline} onChange={updateField} type="date" />
        </label>
        <label>
          Type
          <select name="type" value={form.type} onChange={updateField}>
            <option value="veryShort">Very short</option>
            <option value="short">Short</option>
          </select>
        </label>
      </div>

      <button type="submit" className="primary full-width">
        Create goal
      </button>
    </form>
  );
}
