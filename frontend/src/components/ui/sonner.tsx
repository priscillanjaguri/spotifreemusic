import { Toaster as Sonner, type ToasterProps } from "sonner"
import { CircleCheckIcon, InfoIcon, TriangleAlertIcon, OctagonXIcon, Loader2Icon } from "lucide-react"

const Toaster = ({ ...props }: ToasterProps) => {
  return (
    <Sonner
      theme="light"
      className="toaster group"
      icons={{
        success: <CircleCheckIcon className="size-4 text-heliotrope" />,
        info: <InfoIcon className="size-4 text-wisteria" />,
        warning: <TriangleAlertIcon className="size-4 text-orchid" />,
        error: <OctagonXIcon className="size-4 text-rose" />,
        loading: <Loader2Icon className="size-4 animate-spin" />,
      }}
      style={
        {
          "--normal-bg": "var(--popover)",
          "--normal-text": "var(--popover-foreground)",
          "--normal-border": "var(--color-lavender)",
          "--border-radius": "var(--radius)",
        } as React.CSSProperties
      }
      toastOptions={{
        classNames: {
          toast: "cn-toast !rounded-2xl !shadow-[var(--shadow-whip-lg)]",
          actionButton: "!rounded-full !bg-purple !text-white",
        },
      }}
      {...props}
    />
  )
}

export { Toaster }
