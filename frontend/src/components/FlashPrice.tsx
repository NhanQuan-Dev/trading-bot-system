import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

interface FlashPriceProps {
    value: number;
    prefix?: string;
    suffix?: string;
    className?: string;
    formatter?: (val: number) => string;
}

export function FlashPrice({ value, prefix = "", suffix = "", className, formatter }: FlashPriceProps) {
    const [flashState, setFlashState] = useState<"up" | "down" | null>(null);
    const prevValue = useRef(value);

    useEffect(() => {
        if (value > prevValue.current) {
            setFlashState("up");
        } else if (value < prevValue.current) {
            setFlashState("down");
        }

        prevValue.current = value;

        const timer = setTimeout(() => {
            setFlashState(null);
        }, 1000); // 1s flash duration for visibility

        return () => clearTimeout(timer);
    }, [value]);

    const displayValue = formatter ? formatter(value) : value.toLocaleString();

    return (
        <span
            className={cn(
                "transition-colors duration-500", // Smooth transition
                flashState === "up" && "text-green-500 font-bold animate-pulse",
                flashState === "down" && "text-red-500 font-bold animate-pulse",
                // If not flashing, inherit existing class or default
                !flashState && className
            )}
        >
            {prefix}{displayValue}{suffix}
        </span>
    );
}
