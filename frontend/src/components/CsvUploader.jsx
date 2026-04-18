import { useRef, useState } from "react";

export default function CsvUploader({ onUpload }) {
  const inputRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);

  function handleFiles(files) {
    const file = files?.[0];
    if (file) {
      onUpload(file);
    }
  }

  return (
    <section
      className={`upload-panel ${isDragging ? "dragging" : ""}`}
      onDragOver={(event) => {
        event.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={(event) => {
        event.preventDefault();
        setIsDragging(false);
        handleFiles(event.dataTransfer.files);
      }}
    >
      <div className="section-heading">
        <p className="eyebrow">CSV upload</p>
        <h2>Drop transactions here.</h2>
      </div>
      <p>
        Upload the UCI finance CSV, then Puran will send it through S3, Lambda,
        Bedrock, DynamoDB, and QuickSight.
      </p>
      <input
        ref={inputRef}
        hidden
        type="file"
        accept=".csv,text/csv"
        onChange={(event) => handleFiles(event.target.files)}
      />
      <button type="button" className="primary" onClick={() => inputRef.current?.click()}>
        Choose CSV
      </button>
    </section>
  );
}
