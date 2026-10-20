import axios from "axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:5000/api",
});

export const getEmployees = (search = "", status = "") =>
  api.get("/employees", {
    params: { search, status },
  });

export const createEmployee = (employee) =>
  api.post("/employees", employee);

export const updateEmployee = (id, employee) =>
  api.put(`/employees/${id}`, employee);

export const deleteEmployee = (id) =>
  api.delete(`/employees/${id}`);
