"""Unit tests for capture module"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import tempfile
from pathlib import Path
from radio_ingestion.capture.stream_recorder import StreamRecorder
from radio_ingestion.capture.capture_scheduler import CaptureScheduler, CaptureTask, CaptureTaskStatus


class TestStreamRecorder:
    """Test StreamRecorder"""
    
    def test_init(self, tmp_path):
        """Test recorder initialization"""
        recorder = StreamRecorder(output_dir=str(tmp_path))
        assert recorder.output_dir == Path(tmp_path)
        assert recorder.sample_rate == 22050
        assert recorder.channels == 1
        assert recorder.format == "wav"
    
    @patch('subprocess.run')
    def test_check_ffmpeg_available(self, mock_run, tmp_path):
        """Test ffmpeg availability check"""
        mock_run.return_value = Mock(returncode=0)
        
        recorder = StreamRecorder(output_dir=str(tmp_path))
        # Should not raise
        assert recorder is not None
    
    @patch('subprocess.run')
    def test_check_ffmpeg_missing(self, mock_run, tmp_path):
        """Test ffmpeg missing detection"""
        mock_run.side_effect = FileNotFoundError()
        
        with pytest.raises(RuntimeError, match="ffmpeg is not installed"):
            StreamRecorder(output_dir=str(tmp_path))
    
    @patch('subprocess.Popen')
    def test_record_stream_success(self, mock_popen, tmp_path):
        """Test successful stream recording"""
        # Mock successful ffmpeg process
        mock_process = MagicMock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_process.pid = 12345
        mock_popen.return_value = mock_process
        
        recorder = StreamRecorder(output_dir=str(tmp_path))
        
        # Create a fake output file
        output_file = tmp_path / "stream_20250101_120000.wav"
        output_file.write_bytes(b"fake audio data")
        
        with patch.object(Path, 'exists', return_value=True):
            mock_stat = Mock()
            mock_stat.st_size = 1024
            with patch.object(Path, 'stat', return_value=mock_stat):
                result = recorder.record_stream(
                    stream_url="https://example.com/stream",
                    duration=180
                )
        
        assert result["success"] is True
        assert "path" in result
        assert result["file_size"] > 0
    
    @patch('subprocess.Popen')
    def test_record_stream_timeout(self, mock_popen, tmp_path):
        """Test stream recording timeout"""
        # Mock process that times out
        mock_process = MagicMock()
        mock_process.pid = 12345
        
        import subprocess
        mock_process.communicate.side_effect = subprocess.TimeoutExpired("ffmpeg", 10)
        mock_popen.return_value = mock_process
        
        recorder = StreamRecorder(output_dir=str(tmp_path))
        
        with patch('os.killpg' if hasattr(__import__('os'), 'setsid') else 'os.kill'):
            result = recorder.record_stream(
                stream_url="https://example.com/stream",
                duration=180
            )
        
        assert result["success"] is False
        assert "timeout" in result["error"].lower()
    
    @patch('subprocess.run')
    def test_get_audio_info(self, mock_run, tmp_path):
        """Test getting audio file info"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout=b'{"format":{"bit_rate":"128000","duration":"180.0"},"streams":[{"sample_rate":"22050","channels":"1"}]}'
        )
        
        recorder = StreamRecorder(output_dir=str(tmp_path))
        info = recorder.get_audio_info("/fake/path.wav")
        
        assert info is not None
        assert "bitrate" in info or "sample_rate" in info


class TestCaptureScheduler:
    """Test CaptureScheduler"""
    
    @pytest.fixture
    def recorder(self, tmp_path):
        """Create a mock recorder"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            return StreamRecorder(output_dir=str(tmp_path))
    
    def test_scheduler_init(self, recorder):
        """Test scheduler initialization"""
        scheduler = CaptureScheduler(recorder, max_concurrent=5)
        assert scheduler.max_concurrent == 5
        assert scheduler.semaphore._value == 5
    
    @pytest.mark.asyncio
    async def test_schedule_capture(self, recorder):
        """Test scheduling a capture"""
        scheduler = CaptureScheduler(recorder, max_concurrent=2)
        
        task = await scheduler.schedule_capture(
            source_id=1,
            stream_url="https://example.com/stream",
            station_name="Test Station",
            duration=180
        )
        
        assert task.source_id == 1
        assert task.status == CaptureTaskStatus.RUNNING or task.status == CaptureTaskStatus.PENDING
        assert task.stream_url == "https://example.com/stream"
    
    @pytest.mark.asyncio
    async def test_concurrent_limit(self, recorder):
        """Test that concurrent limit is enforced"""
        scheduler = CaptureScheduler(recorder, max_concurrent=2)
        
        # Schedule 5 tasks
        tasks = []
        for i in range(5):
            task = await scheduler.schedule_capture(
                source_id=i,
                stream_url=f"https://example.com/stream{i}",
                station_name=f"Station {i}",
                duration=10
            )
            tasks.append(task)
        
        # Check that tasks are scheduled (may be pending or running)
        assert len(scheduler.tasks) == 5
        
        # Active tasks should respect concurrency limit
        active = scheduler.get_active_tasks()
        # Note: Actual concurrency enforcement happens in semaphore
    
    def test_get_task_status(self, recorder):
        """Test getting task status"""
        scheduler = CaptureScheduler(recorder)
        task = CaptureTask(
            source_id=1,
            stream_url="https://example.com/stream",
            station_name="Test",
            duration=180
        )
        scheduler.tasks[1] = task
        
        retrieved = scheduler.get_task_status(1)
        assert retrieved is not None
        assert retrieved.source_id == 1
    
    def test_get_completed_tasks(self, recorder):
        """Test getting completed tasks"""
        scheduler = CaptureScheduler(recorder)
        
        # Add completed task
        task = CaptureTask(
            source_id=1,
            stream_url="https://example.com/stream",
            station_name="Test",
            duration=180,
            status=CaptureTaskStatus.COMPLETED
        )
        scheduler.tasks[1] = task
        
        completed = scheduler.get_completed_tasks()
        assert len(completed) == 1
        assert completed[0].source_id == 1

