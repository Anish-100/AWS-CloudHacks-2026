import { useEffect, useRef } from "react";

const circleCount = 28;

export default function FireTrailCursor() {
  const circlesRef = useRef([]);
  const animationRef = useRef(null);

  useEffect(() => {
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (prefersReducedMotion) {
      return undefined;
    }

    const coords = {
      x: window.innerWidth / 2,
      y: window.innerHeight / 2,
    };

    const circles = circlesRef.current;

    circles.forEach((circle) => {
      if (!circle) {
        return;
      }

      circle.x = coords.x;
      circle.y = coords.y;
    });

    function handleMouseMove(event) {
      coords.x = event.clientX;
      coords.y = event.clientY;
    }

    function animateCircles() {
      let x = coords.x;
      let y = coords.y;

      circles.forEach((circle, index) => {
        if (!circle) {
          return;
        }

        const scale = (circles.length - index) / circles.length;
        const heat = Math.max(0.25, scale);

        circle.style.left = `${x}px`;
        circle.style.top = `${y}px`;
        circle.style.transform = `translate(-50%, -50%) scale(${scale})`;
        circle.style.opacity = `${heat}`;

        circle.x = x;
        circle.y = y;

        const nextCircle = circles[index + 1] || circles[0];
        x += (nextCircle.x - x) * 0.36;
        y += (nextCircle.y - y) * 0.36;
      });

      animationRef.current = requestAnimationFrame(animateCircles);
    }

    window.addEventListener("mousemove", handleMouseMove);
    animationRef.current = requestAnimationFrame(animateCircles);

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);

      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, []);

  return (
    <div className="fire-trail" aria-hidden="true">
      {Array.from({ length: circleCount }).map((_, index) => (
        <div
          key={index}
          ref={(element) => {
            circlesRef.current[index] = element;
          }}
          className="fire-circle"
        />
      ))}
    </div>
  );
}
