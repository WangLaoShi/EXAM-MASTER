import { AlertDialog, Button } from '@heroui/react'

interface SubmitConfirmModalProps {
  open: boolean
  unansweredCount: number
  onClose: () => void
  onConfirm: () => void
}

export function SubmitConfirmModal({
  open,
  unansweredCount,
  onClose,
  onConfirm,
}: SubmitConfirmModalProps) {
  if (!open) return null

  return (
    <AlertDialog>
      <AlertDialog.Backdrop isDismissable onClick={onClose}>
        <AlertDialog.Container>
          <AlertDialog.Dialog>
            <AlertDialog.Header>
              <AlertDialog.Heading>确认交卷？</AlertDialog.Heading>
            </AlertDialog.Header>
            <AlertDialog.Body>
              {unansweredCount > 0
                ? `还有 ${unansweredCount} 题未作答，交卷后将进入成绩页。`
                : '所有题目已作答，确认交卷并查看成绩。'}
            </AlertDialog.Body>
            <AlertDialog.Footer>
              <Button variant="outline" onPress={onClose}>
                继续答题
              </Button>
              <Button variant="danger" onPress={onConfirm}>
                确认交卷
              </Button>
            </AlertDialog.Footer>
          </AlertDialog.Dialog>
        </AlertDialog.Container>
      </AlertDialog.Backdrop>
    </AlertDialog>
  )
}
