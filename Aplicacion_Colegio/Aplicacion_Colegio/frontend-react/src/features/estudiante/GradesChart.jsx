import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
} from 'chart.js';
import { Line } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend
);

export default function GradesChart({ chartData }) {
  return (
    <div style={{ width: '100%', maxWidth: '800px', margin: '0 auto', height: '300px' }}>
      <Line 
        data={chartData} 
        options={{
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: {
              min: 1,
              max: 7,
            }
          },
          plugins: {
            legend: {
              position: 'bottom'
            }
          }
        }} 
      />
    </div>
  );
}
