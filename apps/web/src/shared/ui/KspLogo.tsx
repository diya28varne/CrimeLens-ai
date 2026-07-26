import Image from "next/image";

/** Official Karnataka State Police brand mark (high-res asset). */
export function KspLogo({
  size = 160,
  priority = false,
}: {
  size?: number;
  priority?: boolean;
}) {
  return (
    <Image
      src="/branding/karnataka-state-police.png"
      alt="Karnataka State Police"
      width={size}
      height={size}
      priority={priority}
      quality={95}
      style={{
        width: size,
        height: "auto",
        objectFit: "contain",
        display: "block",
        imageRendering: "auto",
      }}
    />
  );
}
