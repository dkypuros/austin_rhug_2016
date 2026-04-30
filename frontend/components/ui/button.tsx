import * as React from "react";
import { clsx } from "clsx";

export type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "default" | "secondary";
};

export function Button({ className, variant = "default", ...props }: ButtonProps) {
  return (
    <button
      className={clsx("button", variant === "secondary" && "button-secondary", className)}
      {...props}
    />
  );
}
