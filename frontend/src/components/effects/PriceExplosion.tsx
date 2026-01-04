
import React, { useEffect, useState, useMemo } from 'react';
import { cn } from '@/lib/utils'; // Assuming this exists given the codebase

interface PriceExplosionProps {
    x: number; // Ignored for now as we center horizontally relative to right edge or similar
    y: number; // Top position
    active: boolean; // Triggers animation on true
    onComplete?: () => void;
}

// Local component definition
const PriceExplosionBase = ({ x, y, active, onComplete }: PriceExplosionProps) => {
    const [isAnimating, setIsAnimating] = useState(false);

    useEffect(() => {
        if (active) {
            setIsAnimating(true);
            const timer = setTimeout(() => {
                setIsAnimating(false);
                if (onComplete) onComplete();
            }, 10000); // 10s total duration
            return () => clearTimeout(timer);
        }
    }, [active, onComplete]);

    // Fragments for the explosion
    // Using 30 emojis as requested
    const particles = useMemo(() => {
        const particleCount = 30;
        // Randomly decide 2 to 3 layers
        const layerCount = 2 + Math.floor(Math.random() * 2);

        return Array.from({ length: particleCount }).map((_, i) => {
            const emojis = ['🚀', '💰', '🤑', '📈', '🔥', '💎', '💸', '🍾'];

            // Assign to a random layer
            const layerIndex = Math.floor(Math.random() * layerCount);

            // Layer properties
            // Stagger layers slightly so they explode in waves
            const layerDelay = layerIndex * 0.2; // 200ms per layer
            // Inner layers might travel less distance? Or random? 
            // Let's keep distance chaotic but roughly uniform to look like a massive burst.

            // Random angle
            const angleDeg = Math.random() * 360;
            const angleRad = (angleDeg * Math.PI) / 180;
            const distance = 150 + Math.random() * 100; // Increased varaiation in distance (150-250)

            const txFinal = Math.cos(angleRad) * distance;
            const tyFinal = Math.sin(angleRad) * distance;

            // Individual random delay to break up uniformity within the layer
            const individualDelay = Math.random() * 0.15;
            const totalDelay = layerDelay + individualDelay;

            // Randomize properties
            const emoji = emojis[Math.floor(Math.random() * emojis.length)];
            const size = 12 + Math.random() * 24; // Slightly larger range: 12-36px

            return (
                <div
                    key={i}
                    className="absolute flex items-center justify-center rounded-full opacity-0 select-none shadow-[0_0_15px_rgba(74,222,128,0.5)] animate-shard"
                    style={{
                        top: '50%',
                        left: '50%',
                        width: `${size * 1.5}px`,
                        height: `${size * 1.5}px`,
                        fontSize: `${size}px`,
                        // Green bubble background with gradient
                        background: 'radial-gradient(circle, rgba(74,222,128,0.4) 0%, rgba(34,197,94,0.1) 70%, transparent 100%)',
                        border: '1px solid rgba(74,222,128,0.3)',
                        transformOrigin: 'center center',

                        // Pass translation deltas to CSS
                        '--tx': `${txFinal}px`,
                        '--ty': `${tyFinal}px`,

                        // Use calculated total delay
                        animation: `shard-burst 9500ms cubic-bezier(0.215, 0.61, 0.355, 1) forwards ${totalDelay}s`,
                    } as React.CSSProperties}
                >
                    {emoji}
                </div>
            );
        });
    }, []); // Empty dependency array ensures particles are generated once per mount

    if (!isAnimating) return null;

    return (
        <div
            className="absolute pointer-events-none z-50"
            style={{
                top: y,
                right: '10px', // Fixed near the price axis
                transform: 'translate(50%, -50%)', // Center on the point
            }}
        >
            {/* Central flash - increased size */}
            <div
                className="absolute top-1/2 left-1/2 w-12 h-12 -translate-x-1/2 -translate-y-1/2 bg-cyan-300 rounded-full blur-xl opacity-0 animate-central-flash"
            />

            {/* Shards container */}
            <div className="relative w-32 h-32 -translate-x-1/2 -translate-y-1/2">
                {particles}
            </div>
        </div>
    );
};

export const PriceExplosion = React.memo(PriceExplosionBase);
export default PriceExplosion;
