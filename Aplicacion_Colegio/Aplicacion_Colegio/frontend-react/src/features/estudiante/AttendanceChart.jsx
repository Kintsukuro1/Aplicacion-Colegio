import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js';
import { Doughnut } from 'react-chartjs-2';

ChartJS.register(ArcElement, Tooltip, Legend);

export default function AttendanceChart({ chartData, totalClasses }) {
  return (
    <div style={{ width: '100%', maxWidth: '300px', margin: '0 auto' }}>
      <Doughnut 
        data={chartData} 
        options={{
          cutout: '70%',
          plugins: {
            legend: {
              position: 'bottom',
              labels: {
                usePointStyle: true,
                padding: 20
              }
            },
            tooltip: {
              callbacks: {
                label: (context) => {
                  const label = context.label || '';
                  const value = context.raw;
                  const percentage = ((value / totalClasses) * 100).toFixed(1);
                  return `${label}: ${value} clases (${percentage}%)`;
                }
              }
            }
          }
        }} 
      />
    </div>
  );
}
