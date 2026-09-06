import { RegisterForm } from "@/components/auth/RegisterForm";

export default function RegisterPage() {
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-semibold">Registrarse</h1>
      <RegisterForm />
    </div>
  );
}
