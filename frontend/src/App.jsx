
import { useCallback, useEffect, useState } from "react";
import "./App.css";

import {
  getEmployees,
  createEmployee,
  updateEmployee,
  deleteEmployee,
} from "./api";

const emptyForm = {
  first_name: "",
  middle_name: "",
  last_name: "",
  email: "",
  date_of_birth: "",
  is_active: true,
};

function App() {
  const [employees, setEmployees] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);

  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const loadEmployees = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const response = await getEmployees(search, status);
      setEmployees(response.data);
    } catch (err) {
      setError(
        err.response?.data?.error ||
          "Could not load employees. Check that Flask is running."
      );
    } finally {
      setLoading(false);
    }
  }, [search, status]);

  useEffect(() => {
    loadEmployees();
  }, [loadEmployees]);

  function handleChange(event) {
    const { name, value, type, checked } = event.target;

    setForm((previous) => ({
      ...previous,
      [name]: type === "checkbox" ? checked : value,
    }));
  }

  function resetForm() {
    setForm({ ...emptyForm });
    setEditingId(null);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setMessage("");

    try {
      if (editingId !== null) {
        await updateEmployee(editingId, form);
        setMessage("Employee updated successfully.");
      } else {
        await createEmployee(form);
        setMessage("Employee added successfully.");
      }

      resetForm();
      await loadEmployees();
    } catch (err) {
      const errors = err.response?.data?.errors;

      setError(
        errors
          ? Object.values(errors).join(" ")
          : err.response?.data?.error ||
              "Could not save employee. Please try again."
      );
    } finally {
      setSaving(false);
    }
  }

  function handleEdit(employee) {
    setEditingId(employee.id);

    setForm({
      first_name: employee.first_name || "",
      middle_name: employee.middle_name || "",
      last_name: employee.last_name || "",
      email: employee.email || "",
      date_of_birth: employee.date_of_birth || "",
      is_active: Boolean(employee.is_active),
    });

    setError("");
    setMessage("");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function handleDelete(id) {
    if (!window.confirm("Are you sure you want to delete this employee?")) {
      return;
    }

    setError("");
    setMessage("");

    try {
      await deleteEmployee(id);

      if (editingId === id) {
        resetForm();
      }

      setMessage("Employee deleted successfully.");
      await loadEmployees();
    } catch (err) {
      setError(
        err.response?.data?.error ||
          "Could not delete employee. Please try again."
      );
    }
  }

  return (
    <main className="container">
      <header className="page-header">
        <div>
          <h1>Employee Management System</h1>
          <p>Manage your employee records in one place.</p>
        </div>
      </header>

      {error && (
        <div className="notice error-notice" role="alert">
          {error}
        </div>
      )}

      {message && (
        <div className="notice success-notice" role="status">
          {message}
        </div>
      )}

      <section className="panel">
        <h2>{editingId !== null ? "Update Employee" : "Add Employee"}</h2>

        <form onSubmit={handleSubmit} className="employee-form">
          <div className="form-field">
            <label htmlFor="first_name">First name</label>
            <input
              id="first_name"
              name="first_name"
              value={form.first_name}
              onChange={handleChange}
              placeholder="Enter first name"
              maxLength={100}
              required
            />
          </div>

          <div className="form-field">
            <label htmlFor="middle_name">Middle name (optional)</label>
            <input
              id="middle_name"
              name="middle_name"
              value={form.middle_name}
              onChange={handleChange}
              placeholder="Enter middle name"
              maxLength={100}
            />
          </div>

          <div className="form-field">
            <label htmlFor="last_name">Last name</label>
            <input
              id="last_name"
              name="last_name"
              value={form.last_name}
              onChange={handleChange}
              placeholder="Enter last name"
              maxLength={100}
              required
            />
          </div>

          <div className="form-field">
            <label htmlFor="email">Email address</label>
            <input
              id="email"
              name="email"
              type="email"
              value={form.email}
              onChange={handleChange}
              placeholder="name@example.com"
              maxLength={150}
              required
            />
          </div>

          <div className="form-field">
            <label htmlFor="date_of_birth">Date of birth</label>
            <input
              id="date_of_birth"
              name="date_of_birth"
              type="date"
              value={form.date_of_birth}
              onChange={handleChange}
              required
            />
          </div>

          <label className="status-checkbox">
            <input
              type="checkbox"
              name="is_active"
              checked={form.is_active}
              onChange={handleChange}
            />
            Active employee
          </label>

          <div className="form-actions">
            <button type="submit" disabled={saving}>
              {saving
                ? "Saving..."
                : editingId !== null
                  ? "Save Changes"
                  : "Add Employee"}
            </button>

            {editingId !== null && (
              <button
                type="button"
                className="secondary-button"
                onClick={resetForm}
                disabled={saving}
              >
                Cancel
              </button>
            )}
          </div>
        </form>
      </section>

      <section className="panel">
        <div className="list-header">
          <div>
            <h2>Employee List</h2>
            <p>{employees.length} employee(s) displayed</p>
          </div>

          <button
            type="button"
            className="secondary-button"
            onClick={loadEmployees}
            disabled={loading}
          >
            Refresh
          </button>
        </div>

        <div className="toolbar">
          <input
            type="search"
            placeholder="Search by name or email..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            aria-label="Search employees"
          />

          <select
            value={status}
            onChange={(event) => setStatus(event.target.value)}
            aria-label="Filter employees by status"
          >
            <option value="">All statuses</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </div>

        {loading ? (
          <p className="empty-state">Loading employees...</p>
        ) : employees.length === 0 ? (
          <p className="empty-state">No employees found.</p>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>First Name</th>
                  <th>Middle Name</th>
                  <th>Last Name</th>
                  <th>Email</th>
                  <th>Date of Birth</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>

              <tbody>
                {employees.map((employee) => (
                  <tr key={employee.id}>
                    <td>{employee.id}</td>
                    <td>{employee.first_name}</td>
                    <td>{employee.middle_name || "—"}</td>
                    <td>{employee.last_name}</td>
                    <td>{employee.email}</td>
                    <td>{employee.date_of_birth}</td>
                    <td>
                      <span
                        className={`status-badge ${
                          employee.is_active ? "active" : "inactive"
                        }`}
                      >
                        {employee.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td>
                      <div className="action-buttons">
                        <button
                          type="button"
                          className="edit-button"
                          onClick={() => handleEdit(employee)}
                        >
                          Edit
                        </button>

                        <button
                          type="button"
                          className="delete-button"
                          onClick={() => handleDelete(employee.id)}
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}

export default App;
